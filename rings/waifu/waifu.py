from __future__ import annotations

import asyncio
import copy
import itertools
import json
import math
import random
from collections import namedtuple
from typing import TYPE_CHECKING, Any, Dict, List, Union

import asyncpg
import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from pathfinding.core.grid import Grid

from rings.utils.checks import has_perms
from rings.utils.converters import (
    FlowerConverter,
    GachaBannerConverter,
    GachaCharacterConverter,
    MemberConverter,
    TimeConverter,
)
from rings.utils.ui import (
    Confirm,
    EmbedDefaultConverter,
    EmbedChoiceConverter,
    EmbedIterableConverter,
    EmbedRangeConverter,
    EmbedStringConverter,
    MultiInputEmbedView,
    paginate,
)
from rings.utils.utils import BotError, DatabaseError, check_channel

from .base import DUD_TEMPLATES, POSITION_EMOJIS, Stat, StatBlock
from .battle import Battle, Battlefield, Character, is_wakable
from .enemies import POTENTIAL_ENEMIES
from .entities import StattedEntity
from .fields import POTENTIAL_FIELDS
from .skills import get_skill
from .ui import CombatView, EmbedSkillConverter, EmbedStatConverter

if TYPE_CHECKING:
    from bot import NecroBot

LOG_SIZE = 7
EquipmentSet = namedtuple("EquipmentSet", "character weapon artefact")


class Flowers(commands.Cog):
    """A server specific economy system. Use it to reward/punish users at you heart's content. Also contains a gacha system."""

    def __init__(self, bot: NecroBot):
        self.bot = bot

        self.DUD_PERCENT = 0.33

    #######################################################################
    ## Cog Functions
    #######################################################################

    def cog_check(self, ctx: commands.Context[NecroBot]):
        if ctx.guild:
            return True

        raise commands.CheckFailure("This command cannot be used in private messages.")

    #######################################################################
    ## Functions
    #######################################################################

    async def add_flowers(self, guild_id: int, user_id: int, amount: int):
        await self.bot.db.query(
            "UPDATE necrobot.Flowers SET flowers = flowers + $3 WHERE guild_id=$1 AND user_id=$2",
            guild_id,
            user_id,
            amount,
        )

    async def transfer_flowers(self, guild_id: int, payer: int, payee: int, amount: int):
        await self.add_flowers(guild_id, payer, -amount)
        await self.add_flowers(guild_id, payee, amount)

    async def get_flowers(self, guild_id: int, user_id: int) -> int:
        flowers = await self.bot.db.query(
            "SELECT flowers FROM necrobot.Flowers WHERE guild_id=$1 AND user_id=$2",
            guild_id,
            user_id,
        )

        return flowers[0][0]

    async def get_symbol(self, guild_id: int) -> str:
        symbol = await self.bot.db.query(
            "SELECT symbol FROM necrobot.FlowersGuild WHERE guild_id=$1", guild_id
        )

        return symbol[0][0]

    async def update_symbol(self, guild_id: int, symbol: str):
        await self.bot.db.query(
            "UPDATE necrobot.FlowersGuild SET symbol=$2 WHERE guild_id=$1",
            guild_id,
            symbol,
        )

    async def get_balance(self, ctx: commands.Context[NecroBot], user: discord.Member):
        if user is None:
            user = ctx.author

        flowers = await self.get_flowers(ctx.guild.id, user.id)
        symbol = await self.get_symbol(ctx.guild.id)

        await ctx.send(f":atm: | {user.name} has **{flowers}** {symbol}")

    async def add_characters_to_user(self, guild_id: int, user_id: int, char_id: int):
        query = await self.bot.db.query(
            """
            INSERT INTO necrobot.RolledCharacters(guild_id, user_id, char_id) VALUES($1, $2, $3)
            ON CONFLICT (guild_id, user_id, char_id)
            DO UPDATE SET level = RolledCharacters.level + 1 RETURNING RolledCharacters.level;
        """,
            guild_id,
            user_id,
            char_id,
            fetchval=True,
        )

        return query

    async def remove_character_from_user(self, guild_id: int, user_id: int, char_id: int, amount: int):
        conn = await self.bot.db.get_conn()
        async with conn.transaction():
            level = await self.bot.db.query(
                "UPDATE necrobot.RolledCharacters SET level = level - $4 WHERE guild_id = $1 AND user_id=$2 AND char_id=$3 RETURNING level;",
                guild_id,
                user_id,
                char_id,
                amount,
                fetchval=True,
            )

            deleted = await self.bot.db.query(
                "DELETE FROM necrobot.RolledCharacters WHERE guild_id = $1 AND user_id=$2 AND char_id=$3 AND level < 1 RETURNING char_id;",
                guild_id,
                user_id,
                char_id,
                fetchval=True,
            )

        return level, deleted

    def convert_exp_to_level(self, exp: int, tier: int) -> int:
        level = 0
        thresholds = [
            1,
            3,
            5,
            7,
            10,
        ]

        for threshold in thresholds:
            true_threshold = (6 - tier) * threshold
            if exp >= true_threshold:
                level += 1
                exp -= true_threshold
            else:
                break
        else:
            true_threshold = 0

        return level, exp, true_threshold

    def calculate_weight(self, tier: int, modifier: int, pity: int) -> int:
        weight = (2 ** (1 + (5 - tier))) * modifier

        if tier != 5:
            return weight

        pity_pass = random.choices([False, True], [60, pity])
        if pity_pass[0]:
            weight = weight + max(0, pity - 30)

        return weight

    def embed_character(self, character: dict, admin: bool = False) -> discord.Embed:
        embed = discord.Embed(
            title=character["name"],
            colour=self.bot.bot_color,
            description=character["description"],
        )

        if url := character.get("image_url"):
            embed.set_image(url=url)

        embed.set_footer(**self.bot.bot_footer)

        if char_id := character.get("id"):
            embed.add_field(name="ID", value=char_id)

        embed.add_field(name="Title", value=character["title"])
        embed.add_field(
            name="Tier",
            value=f"{character['tier']*':star:' if character['tier'] else ':fleur_de_lis:'}",
        )
        embed.add_field(name="Universe", value=character["universe"])

        if level := character.get("level"):
            level, exp, next_threshold = self.convert_exp_to_level(level, character["tier"])
            embed.add_field(name="Level", value=f"{level} ({exp}/{next_threshold})")

        if admin and character.get("obtainable"):
            embed.add_field(name="Obtainable", value=character["obtainable"])

        if char_type := character.get("type"):
            embed.add_field(name="Type", value=char_type.title())

        stats = f"- Health: {self.c(character['primary_health'])} ({self.c(character['secondary_health'])})\n- PA: {self.c(character['physical_attack'])}\n- MA: {self.c(character['magical_attack'])}\n- PD: {self.c(character['physical_defense'])}\n- MD: {self.c(character['magical_defense'])}"
        embed.add_field(name="Stats", value=stats, inline=False)

        embed.add_field(
            name="Abilities",
            value=f"- Active: {character['active_skill']}\n- Passive: {character['passive_skill']}",
        )
        return embed

    def c(self, s: Any) -> Stat:
        if isinstance(s, asyncpg.Record):
            return Stat.from_db(s)

        return s

    def embed_banner(self, banner: Dict, admin: bool = False) -> discord.Member:
        embed = discord.Embed(
            title=f"{banner['name']}",
            colour=self.bot.bot_color,
            description=banner["description"],
        )

        if banner.get("image_url"):
            embed.set_image(url=banner["image_url"])

        embed.set_footer(**self.bot.bot_footer)

        if admin and banner.get("ongoing"):
            embed.add_field(name="Ongoing", value=banner["ongoing"])

        embed.add_field(name="Characters", value="\n".join(banner["characters"]))

        if banner.get("id"):
            embed.add_field(name="ID", value=banner["id"])

        if banner.get("max_rolls") is not None:
            embed.add_field(
                name="Max Rolls",
                value=banner["max_rolls"] if banner["max_rolls"] > 0 else "No max",
            )

        return embed

    async def pay_for_roll(self, guild_id: int, user_id: int, cost: int):
        await self.bot.db.query(
            """
            UPDATE necrobot.Flowers SET flowers = flowers - $3 WHERE user_id = $2 AND guild_id = $1""",
            guild_id,
            user_id,
            cost,
        )

    async def get_characters(self):
        return await self.bot.db.query(
            "SELECT * FROM necrobot.Characters ORDER BY tier DESC, universe ASC, name ASC"
        )

    def pull(self, characters: List[dict], pity: int = 0, guarantee: bool = False):
        duds = [
            random.choice(DUD_TEMPLATES)
            for _ in range(math.ceil(len(characters) * self.DUD_PERCENT))
        ]
        pool = [*characters, *duds]
        weights = [self.calculate_weight(char["tier"], char["modifier"], pity) for char in pool]

        pulled_char = dict(random.choices(pool, weights=weights, k=1)[0])

        if pulled_char["tier"] < 4 and guarantee:
            tier_4_list = [char for char in characters if char["tier"] == 4]
            if tier_4_list:
                return dict(random.choice(tier_4_list)), True

            tier_3_list = [char for char in characters if char["tier"] == 3]
            if tier_3_list:
                return dict(random.choice(tier_3_list)), True

        return pulled_char, pulled_char["tier"] >= 4

    #######################################################################
    ## Commands
    #######################################################################

    @commands.group(invoke_without_command=True, aliases=["flower"])
    @has_perms(3)
    async def flowers(
        self,
        ctx: commands.Context[NecroBot],
        member: MemberConverter,
        amount: int,
        *,
        reason: str = None,
    ):
        """Award flowers to a user, can be a negative value to take away flowers.

        {usage}

        __Examples__
        `{pre}flowers 1000 @APerson` - awards 1000 flowers to user APerson
        `{pre}flowers 1000 @APerson for being good` - awards 1000 flowers to user APerson with a reason
        `{pre}flowers -1000 @APerson` - take 1000 flowers to user APerson

        """
        if amount < 0:
            msg = ":white_check_mark: | Took **{amount}** {symbol} from **{member.display_name}**"
        else:
            msg = ":white_check_mark: | Awarded **{amount}** {symbol} to **{member.display_name}**"

        if reason:
            msg += f" for *{reason}*"

        await self.add_flowers(ctx.guild.id, member.id, amount)
        await ctx.send(
            msg.format(
                amount=abs(amount),
                symbol=await self.get_symbol(ctx.guild.id),
                member=member,
            )
        )

    @flowers.command(name="symbol")
    @has_perms(4)
    async def flowers_symbol(self, ctx: commands.Context[NecroBot], symbol: str):
        """Change the symbol for the flowers for your server. Max 50 char.

        {usage}

        __Examples__
        `{pre}flowers symbol :arrow:` - change it to the arrow emoji
        """
        if len(symbol) > 50:
            raise BotError(f"Cannot be more than 50 characters. ({len(symbol)}/50")

        await self.update_symbol(ctx.guild.id, symbol)
        await ctx.send(":white_check_mark: | Updated!")

    @flowers.command(name="balance")
    @commands.guild_only()
    async def flowers_balance(self, ctx: commands.Context[NecroBot], user: discord.Member = None):
        """Check your or a user's balance of flowers

        {usage}

        __Examples__
        `{pre}$` - check you own balance
        `{pre}$ @Necro` - check the user Necro's balance
        """
        await self.get_balance(ctx, user)

    @commands.command()
    @has_perms(3)
    async def event(
        self,
        ctx: commands.Context[NecroBot],
        channel: Union[discord.Thread, discord.TextChannel],
        amount: int,
        time: TimeConverter = 86400,
    ):
        """Create a 24hr message, if reacted to, the use who reacted will be granted flowers. Time arguments uses standard
        necrobot time system. The following times can be used: days (d), hours (h), minutes (m), seconds (s).

        {usage}

        __Examples__
        `{pre}flowerevent #lounge 1500` - creates a 24hr event that awards 1500 on reaction in lounge.
        `{pre}flowerevent #lounge 1500 2d` - creates a 48hr event that awards 1500 on reaction in lounge.
        """
        check_channel(channel)

        symbol = await self.get_symbol(ctx.guild.id)

        if time > 3600:
            time_format = f"{time/3600} hour(s)"
        else:
            time_format = f"{time/60} minute(s)"

        embed = discord.Embed(
            color=self.bot.bot_color,
            title="Flower Event",
            description=f"React with :cherry_blossom: to gain **{amount}** {symbol}. This event will last {time_format}",
        )
        embed.set_footer(**self.bot.bot_footer)
        msg: discord.Message = await channel.send(embed=embed, delete_after=time)
        await msg.add_reaction("\N{CHERRY BLOSSOM}")
        self.bot.events[msg.id] = {"users": [], "amount": amount}

    @commands.command()
    @commands.guild_only()
    async def give(self, ctx: commands.Context[NecroBot], member: MemberConverter, amount: FlowerConverter):
        """Transfer flowers from one user to another.

        {usage}

        __Examples__
        `{pre}give 100 @ThisGuy` - give 100 flowers to user ThisGuy"""
        await self.transfer_flowers(ctx.guild.id, ctx.author.id, member.id, amount)

        symbol = await self.get_symbol(ctx.guild.id)
        await ctx.send(
            f":white_check_mark: | **{ctx.author.display_name}** has gifted **{amount}** {symbol} to **{member.display_name}**"
        )

    ###GACHA
    @commands.group(invoke_without_command=True, aliases=["char", "character"])
    async def characters(self, ctx: commands.Context[NecroBot], for_banner: bool = False):
        """List all possible characters

        {usage}

        __Examples__
        `{pre}characters` - List all characters
        `{pre}characters true` - List all characters that can be added to a banner
        """
        characters = await self.get_characters()

        if for_banner:
            characters = [character for character in characters if character["obtainable"]]

        def embed_maker(view, entry):
            mutable_entry = dict(entry)
            mutable_entry["name"] = f"{entry['name']} ({view.page_number}/{view.page_count})"
            return self.embed_character(mutable_entry, True)

        await paginate(ctx, characters, 1, embed_maker)

    @characters.command(name="list")
    async def characters_list(self, ctx: commands.Context[NecroBot]):
        """Compact list of characters

        {usage}

        __Examples__
        `{pre}characters list` - list characters
        """
        characters = await self.get_characters()

        def embed_maker(view, entries):
            description = "\n".join(
                [
                    f"- {entry['id']} - {entry['name']} ({entry['universe']}): **{entry['tier']}**:star:"
                    for entry in entries
                ]
            )
            embed = discord.Embed(
                title=f"Character List ({view.page_number}/{view.page_count})",
                colour=self.bot.bot_color,
                description=description,
            )
            embed.set_footer(**self.bot.bot_footer)

            return embed

        await paginate(ctx, characters, 10, embed_maker)

    @characters.command(name="get")
    async def characters_get(self, ctx: commands.Context[NecroBot], character: GachaCharacterConverter):
        """Get info on a specific character.

        {usage}

        __Example__
        `{pre}characters get Amelan` - get info on the character called Amelan.
        """
        await ctx.send(embed=self.embed_character(character, True))

    async def character_editor(self, ctx: commands.Context[NecroBot], name: str, char_id: str, defaults: Dict[str, EmbedDefaultConverter]):
        def embed_maker(values):
            return self.embed_character(
                {
                    "name": name,
                    "description": values["description"],
                    "image_url": values["image"],
                    "title": values["title"],
                    "tier": values["tier"],
                    "universe": values["universe"],
                    "obtainable": False,
                    "id": char_id,
                    "type": values["type"],
                    "primary_health": values["primary_health"],
                    "secondary_health": values["secondary_health"],
                    "physical_attack": values["physical_attack"],
                    "magical_attack": values["magical_attack"],
                    "physical_defense": values["physical_defense"],
                    "magical_defense": values["magical_defense"],
                    "passive_skill": values["passive_skill"],
                    "active_skill": values["active_skill"],
                }
            )

        view = MultiInputEmbedView(embed_maker, defaults, "Character Edit", ctx.author)
        view.message = await ctx.send(
            "You can submit the edit form anytime. Missing field will only be checked on confirmation.",
            embed=await view.generate_embed(),
            view=view,
        )

        await view.wait()
        return view

    @characters.command(name="create")
    @has_perms(6)
    async def characters_create(self, ctx: commands.Context[NecroBot], *, name: str):
        """Add a new character

        {usage}

        __Examples__
        `{pre}characters create John` - Start the creation process.
        """
        defaults = {
            "description": EmbedStringConverter(style=discord.TextStyle.paragraph),
            "image": EmbedStringConverter(optional=True),
            "title": EmbedStringConverter(),
            "tier": EmbedRangeConverter(min=1, max=5),
            "universe": EmbedStringConverter(),
            "type": EmbedChoiceConverter(choices=["character", "weapon", "artefact"]),
            "primary_health": EmbedStatConverter(),
            "secondary_health": EmbedStatConverter(),
            "physical_attack": EmbedStatConverter(),
            "magical_attack": EmbedStatConverter(),
            "physical_defense": EmbedStatConverter(),
            "magical_defense": EmbedStatConverter(),
            "passive_skill": EmbedSkillConverter(optional=True, passive=True),
            "active_skill": EmbedSkillConverter(optional=True),
        }

        view = await self.character_editor(ctx, name, None, defaults)
        if not view.value:
            return

        final_values = view.convert_values()
        char_id = await self.bot.db.query(
            "INSERT INTO necrobot.Characters VALUES(DEFAULT, $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16) RETURNING id",
            name,
            final_values["title"],
            final_values["description"],
            final_values["image"],
            final_values["tier"],
            False,
            final_values["universe"],
            final_values["type"],
            final_values["active_skill"],
            final_values["passive_skill"],
            final_values["primary_health"].to_db(),
            final_values["secondary_health"].to_db(),
            final_values["physical_defense"].to_db(),
            final_values["physical_attack"].to_db(),
            final_values["magical_defense"].to_db(),
            final_values["magical_attack"].to_db(),
            fetchval=True,
        )

        await ctx.send(f"Character creation done! ID is **{char_id}**")

    @characters.command(name="edit")
    @has_perms(6)
    async def characters_edit(
        self,
        ctx: commands.Context[NecroBot],
        char: GachaCharacterConverter,
    ):
        """Edit a character's value

        {usage}

        __Example__
        `{pre}characters edit Amelan title Big Boy` - Edit Amelan's title to "Big Boy"
        """
        char_id = char["id"]
        defaults = {
            "description": EmbedStringConverter(
                default=char["description"], style=discord.TextStyle.paragraph
            ),
            "image": EmbedStringConverter(default=char["image_url"], optional=True),
            "title": EmbedStringConverter(default=char["title"]),
            "tier": EmbedRangeConverter(default=char["tier"], min=1, max=5),
            "universe": EmbedStringConverter(default=char["universe"]),
            "type": EmbedChoiceConverter(
                default=char["type"], choices=["character", "weapon", "artefact"]
            ),
            "primary_health": EmbedStatConverter(default=char["primary_health"]),
            "secondary_health": EmbedStatConverter(default=char["secondary_health"]),
            "physical_attack": EmbedStatConverter(default=char["physical_attack"]),
            "magical_attack": EmbedStatConverter(default=char["magical_attack"]),
            "physical_defense": EmbedStatConverter(default=char["physical_defense"]),
            "magical_defense": EmbedStatConverter(default=char["magical_defense"]),
            "passive_skill": EmbedStringConverter(optional=True),
            "active_skill": EmbedStringConverter(optional=True),
        }

        view = await self.character_editor(ctx, char["name"], char["id"], defaults)
        if not view.value:
            return

        final_values = view.convert_values()
        await self.bot.db.query(
            """
                UPDATE necrobot.Characters 
                SET 
                    title = $1, 
                    description = $2, 
                    image_url = $3, 
                    tier = $4, 
                    universe = $5,
                    primary_health = $6,
                    secondary_heath = $7,
                    physical_defense = $8,
                    physical_attack = $9,
                    magical_defense = $10,
                    magical_attack = $11,
                    active_skill = $12,
                    passive_skill = $13, 
                WHERE id = $14;""",
            final_values["title"],
            final_values["description"],
            final_values["image"],
            final_values["tier"],
            final_values["universe"],
            final_values["type"],
            final_values["primary_health"].to_db(),
            final_values["secondary_health"].to_db(),
            final_values["physical_defense"].to_db(),
            final_values["physical_attack"].to_db(),
            final_values["magical_defense"].to_db(),
            final_values["magical_attack"].to_db(),
            final_values["active_skill"],
            final_values["passive_skill"],
            char["id"],
        )

        await ctx.send("Character edition done!")

    @characters.command(name="delete")
    @has_perms(6)
    async def characters_delete(self, ctx: commands.Context[NecroBot], char: GachaCharacterConverter):
        """Delete a character and remove them from all player's accounts

        {usage}

        __Examples__
        `{pre}characters delete 12141` - Delete the character
        """
        view = Confirm(ctx.author)
        view.message = await ctx.send(
            "Are you sure you want to delete this character?",
            view=view,
            embed=self.embed_character(char),
        )
        await view.wait()
        if not view.value:
            return

        query = await self.bot.db.query(
            "DELETE FROM necrobot.Characters WHERE id=$1 RETURNING name;",
            char["id"],
            fetchval=True,
        )

        await view.message.send(
            content=f":white_check_mark: | Character **{query[0]}** deleted and removed.",
            embed=None,
        )

    @characters.command(name="toggle")
    @has_perms(6)
    async def characters_toggle(self, ctx: commands.Context[NecroBot], char: GachaCharacterConverter):
        """Toggle whether or not a character can be obtained as part of a banner

        {usage}

        __Examples__
        `{pre}characters toggle 12141` - Toggle a character
        """
        query = await self.bot.db.query(
            "UPDATE necrobot.Characters SET obtainable=not obtainable WHERE id=$1 RETURNING (name, obtainable);",
            char["id"],
            fetchval=True,
        )
        await ctx.send(
            f":white_check_mark: | Character **{query[0]}** is now {'not ' if not query[1] else ''}obtainable."
        )

    @characters.command(name="give")
    @has_perms(4)
    async def characters_give(
        self,
        ctx: commands.Context[NecroBot],
        user: MemberConverter,
        char: GachaCharacterConverter(allowed_types=("character", "artefact", "weapon")),
    ):
        """Add a level of character to a player's account

        {usage}

        __Examples__
        `{pre}characters give @Necro 12141` - Give one level of character 12141 to Necro
        """
        view = Confirm(ctx.author)
        view.message = await ctx.send(
            f"Are you sure you want to give this character to {user.display_name}?",
            view=view,
            embed=self.embed_character(char),
        )
        await view.wait()
        if not view.value:
            return

        await asyncio.sleep(1)
        level = await self.add_characters_to_user(ctx.guild.id, user.id, char["id"])
        await view.message.edit(
            content=f":white_check_mark: | Added **{char['id']}** to user's rolled characters (New: {level == 1})",
            embed=None,
        )

    @characters.command(name="take")
    @has_perms(4)
    async def characters_take(
        self,
        ctx: commands.Context[NecroBot],
        user: MemberConverter,
        char: GachaCharacterConverter(allowed_types=("character", "artefact", "weapon")),
        amount: int = 1,
    ):
        """Remove a level of character to a player's account

        {usage}

        __Examples__
        `{pre}characters take @Necro 12141` - Remove one level of character 12141 from Necro
        """
        view = Confirm(ctx.author)
        view.message = await ctx.send(
            f"Are you sure you want to remove this character from {user.display_name}?",
            view=view,
            embed=self.embed_character(char),
        )
        await view.wait()
        if not view.value:
            return

        level, is_deleted = await self.remove_character_from_user(
            ctx.guild.id, user.id, char["id"], amount
        )
        if not level and not is_deleted:
            await view.message.edit(
                content=":negative_squared_cross_mark: | User does not have that character",
                embed=None,
            )
        else:
            await view.message.edit(
                content=f":white_check_mark: | Amount taken from user's rolled characters (Deleted: {bool(is_deleted)})",
                embed=None,
            )

    @commands.group(invoke_without_command=True, aliases=["banner"])
    @commands.guild_only()
    async def banners(self, ctx: commands.Context[NecroBot], archive: bool = False):
        """List ongoing banners

        {usage}

        __Examples__
        `{pre}characters` - List ongoing banners
        `{pre}characters true` - List all ongoing and ended banners
        """
        if archive:
            banners = await self.bot.db.query(
                """
                SELECT b.*, json_agg(json_build_array(c.name, c.tier)) as characters FROM necrobot.Banners AS b 
                    JOIN necrobot.BannerCharacters AS bc ON b.id=bc.banner_id 
                    JOIN necrobot.Characters as c ON bc.char_id=c.id
                WHERE guild_id=$1
                GROUP BY b.id
            """,
                ctx.guild.id,
            )
        else:
            banners = await self.bot.db.query(
                """
                SELECT b.*, json_agg(json_build_array(c.name, c.tier)) as characters FROM necrobot.Banners AS b 
                    JOIN necrobot.BannerCharacters AS bc ON b.id=bc.banner_id 
                    JOIN necrobot.Characters as c ON bc.char_id=c.id
                WHERE guild_id=$1 AND ongoing=$2
                GROUP BY b.id
            """,
                ctx.guild.id,
            )

        def embed_maker(view, entry):
            mutable_entry = dict(entry)
            mutable_entry["name"] = f"{entry['name']} ({view.page_number}/{view.page_count})"
            mutable_entry["characters"] = [
                f"{char[0]} ({char[1]} :star:)" for char in json.loads(entry["characters"])
            ]
            return self.embed_banner(mutable_entry, archive)

        await paginate(ctx, banners, 1, embed_maker)

    @banners.command(name="create")
    @has_perms(4)
    async def banners_create(self, ctx: commands.Context[NecroBot], *, name: str):
        """Add a new banner in the guild.

        {usage}

        __Examples__
        `{pre}banner create Rose Lily Banner` - Start the creation for a banner
        """
        banner_id = None

        async def embed_maker(values: dict):
            chars = []
            if values.get("characters") is not None:
                chars = [
                    await GachaCharacterConverter(
                        respect_obtainable=True, allowed_types=("character", "artefact", "weapon")
                    ).convert(ctx, char)
                    for char in values["characters"]
                ]

            return self.embed_banner(
                {
                    "id": banner_id,
                    "image_url": values["image"],
                    "description": values["description"],
                    "characters": [f"{char['name']} ({char['tier']} :star:)" for char in chars],
                    "name": name,
                    "max_rolls": values["max_rolls"],
                }
            )

        defaults = {
            "description": EmbedStringConverter(style=discord.TextStyle.paragraph),
            "image": EmbedStringConverter(optional=True),
            "characters": EmbedIterableConverter(),
            "max_rolls": EmbedRangeConverter(min=0, default="0"),
        }

        view = MultiInputEmbedView(embed_maker, defaults, "Banner Edit", ctx.author)
        msg = await ctx.send(
            "You can submit the edit form anytime. Missing field will only be checked on confirmation. \n Characters is a comma separate list of characters (name or ID)",
            embed=await view.generate_embed(),
            view=view,
        )

        await view.wait()
        if not view.value:
            return

        final_values = view.convert_values()
        banner_id = await self.bot.db.query(
            "INSERT INTO necrobot.Banners(guild_id, name, description, image_url, max_rolls) VALUES($1, $2, $3, $4, $5) RETURNING id",
            ctx.guild.id,
            name,
            final_values["description"],
            final_values["image"],
            final_values["max_rolls"],
            fetchval=True,
        )

        chars = [
            await GachaCharacterConverter(
                respect_obtainable=True, allowed_types=("character", "artefact", "weapon")
            ).convert(ctx, char)
            for char in final_values["characters"]
        ]
        await self.bot.db.query(
            "INSERT INTO necrobot.BannerCharacters VALUES($1, $2, $3)",
            [(banner_id, char["id"], 1) for char in chars],
            many=True,
        )

        await ctx.send(f"Banner creation done with ID **{banner_id}**!")

    @banners.command(name="toggle")
    @has_perms(4)
    async def banners_toggle(self, ctx: commands.Context[NecroBot], banner: GachaBannerConverter(False)):
        """Toggle whether or not a banner is currently running

        {usage}

        __Examples__
        `{pre}banner toggle 12141` - Toggle a banner
        """
        query = await self.bot.db.query(
            "UPDATE necrobot.Banners SET ongoing=not ongoing WHERE id=$1 RETURNING (name, ongoing);",
            banner["id"],
            fetchval=True,
        )
        await ctx.send(
            f":white_check_mark: | Banner **{query[0]}** is now {'not ' if not query[1] else ''}ongoing."
        )

    @banners.command(name="add")
    @has_perms(4)
    async def banners_add(
        self,
        ctx: commands.Context[NecroBot],
        banner: GachaBannerConverter(False),
        *,
        char: GachaCharacterConverter(allowed_types=("character", "artefact", "weapon")),
    ):
        """Add characters to a banner

        {usage}

        __Examples__
        `{pre}banners add 12141 John the Smith` - add character John to the banner
        """
        try:
            await self.bot.db.query(
                """
                INSERT INTO necrobot.BannerCharacters(banner_id, char_id) VALUES($1, $2)
                """,
                banner["id"],
                char["id"],
            )
            await ctx.send(
                f":white_check_mark: | Character **{char['name']}** added to banner **{banner['name']}**."
            )
        except Exception:
            raise BotError(f"Character **{char['name']}** already in banner **{banner['name']}**.")

    @banners.command(name="remove")
    @has_perms(4)
    async def banners_remove(
        self,
        ctx: commands.Context[NecroBot],
        banner: GachaBannerConverter(False),
        *,
        char: GachaCharacterConverter(allowed_types=("character", "artefact", "weapon")),
    ):
        """Remove characters from a banner

        {usage}

        __Examples__
        `{pre}banners remove 12141 John the Smith` - remove character John from the banner
        """
        is_deleted = await self.bot.db.query(
            """
            DELETE FROM necrobot.BannerCharacters WHERE banner_id = $1 AND char_id = $2 RETURNING char_id
            """,
            banner["id"],
            char["id"],
        )

        if is_deleted:
            await ctx.send(
                f":white_check_mark: | Characters **{char['name']}** removed from banner **{banner['name']}**."
            )
        else:
            raise BotError(
                f"Characters **{char['name']}** not present on banner **{banner['name']}**."
            )

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def gacha(self, ctx: commands.Context[NecroBot]):
        """Get information on the gacha on this server

        {usage}

        __Examples__
        `{pre}gacha` - get information on the gacha in this server
        """
        guild = await self.bot.db.query(
            "SELECT roll_cost, symbol, guaranteed FROM necrobot.FlowersGuild WHERE guild_id = $1",
            ctx.guild.id,
        )
        if guild[0]["guaranteed"] >= 0:
            guarantee = (
                f"You are guaranteed a character after **{guild[0]['guaranteed'] + 1}** rolls."
            )
        else:
            guarantee = "You are not guaranteed a character after any amount of rolls."

        await ctx.send(
            f":game_die: | A roll on this server costs **{guild[0]['roll_cost']}** {guild[0]['symbol']}.\n:star2: | {guarantee}"
        )

    @gacha.command(name="balance")
    @commands.guild_only()
    async def gacha_balance(self, ctx: commands.Context[NecroBot], user: MemberConverter = None):
        """Check your or a user's balance of flowers

        {usage}

        __Examples__
        `{pre}$` - check you own balance
        `{pre}$ @Necro` - check the user Necro's balance
        """
        await self.get_balance(ctx, user)

    @gacha.command(name="characters", aliases=["char", "character"])
    @commands.guild_only()
    async def gacha_characters(self, ctx: commands.Context[NecroBot]):
        """List all your characters and their info.

        {usage}

        __Examples__
        `{pre}gacha char` - List your characters"""
        characters = await self.bot.db.query(
            """
            SELECT c.*, rc.level FROM necrobot.RolledCharacters as rc 
                JOIN necrobot.Characters as c ON rc.char_id = c.id 
            WHERE rc.guild_id = $1 AND rc.user_id = $2
            ORDER BY c.universe, c.name""",
            ctx.guild.id,
            ctx.author.id,
        )

        def embed_maker(view, entry):
            mutable_entry = dict(entry)
            mutable_entry["name"] = f"{entry['name']} ({view.page_number}/{view.page_count})"
            return self.embed_character(mutable_entry)

        await paginate(ctx, characters, 1, embed_maker)

    @gacha.group(name="roll", invoke_without_command=True, aliases=["pull"])
    @commands.guild_only()
    @commands.max_concurrency(1, per=BucketType.user, wait=True)
    async def gacha_roll(self, ctx: commands.Context[NecroBot], *, banner: GachaBannerConverter):
        """Roll for a banner.

        {usage}

        __Examples__
        `{pre}gacha roll 1` - roll on banner with id 1
        """
        pity = 0
        guarantee = False
        roll_count = 0

        query = await self.bot.db.query(
            "SELECT tier_5_pity, tier_4_pity, roll_count FROM necrobot.Pity WHERE user_id = $1 AND banner_id = $2",
            ctx.author.id,
            banner["id"],
        )
        data = await self.bot.db.query(
            "SELECT symbol, roll_cost, guaranteed FROM necrobot.FlowersGuild WHERE guild_id = $1",
            ctx.guild.id,
        )

        if query:
            pity = query[0]["tier_5_pity"]
            guarantee = (
                query[0]["tier_4_pity"] >= data[0]["guaranteed"] and data[0]["guaranteed"] >= 0
            )
            roll_count = query[0]["roll_count"]

        if banner["max_rolls"] > 0 and roll_count >= banner["max_rolls"]:
            raise BotError("You've hit the max amount of rolls on this banner.")

        characters = await self.bot.db.query(
            """
            SELECT c.*, bc.modifier FROM necrobot.BannerCharacters as bc 
                JOIN necrobot.Characters as c ON bc.char_id = c.id 
            WHERE bc.banner_id = $1
            ORDER BY c.universe, c.name""",
            banner["id"],
        )

        mutable_banner = dict(banner)
        mutable_banner["characters"] = [
            f"{char['name']} ({char['tier']} :star:)" for char in characters
        ]

        view = Confirm(ctx.author, confirm_msg=None)
        view.message = await ctx.send(
            f"Roll on this banner for **{data[0]['roll_cost']}** {data[0]['symbol']}?",
            embed=self.embed_banner(mutable_banner),
            view=view,
        )
        await view.wait()
        if not view.value:
            return

        try:
            await self.pay_for_roll(ctx.guild.id, ctx.author.id, data[0]["roll_cost"])
        except Exception as e:
            raise BotError("You no longer have enough flowers for a pull.") from e

        pulled_char, guaranteed = self.pull(characters, pity, guarantee)

        sleep = 5
        if pulled_char["tier"] == 5:
            pity_increase = -1
            pull_animation = "https://media.tenor.com/rOuL0G1uRpMAAAAd/genshin-impact-pull.gif"
        elif pulled_char["tier"] == 4:
            pity_increase = 3
            pull_animation = (
                "https://media.tenor.com/pVzBgcp1RPQAAAAd/genshin-impact-animation.gif"
            )
        else:
            sleep = 2
            pity_increase = 2
            pull_animation = "https://media.tenor.com/-0gPdn6GMVAAAAAC/genshin3star-wish.gif"

        if pulled_char.get("id"):  # not a dud
            level = await self.add_characters_to_user(
                ctx.guild.id, ctx.author.id, pulled_char["id"]
            )
            pulled_char["level"] = level
        else:
            pity = 1

        await asyncio.sleep(0.5)
        await view.message.edit(embed=discord.Embed().set_image(url=pull_animation))
        await asyncio.sleep(sleep)
        await view.message.edit(
            content=f":game_die: | You paid **{data[0]['roll_cost']}** {data[0]['symbol']} and got the following reward:",
            embed=self.embed_character(pulled_char),
        )

        if guaranteed:
            guarantee_change = -query[0]["tier_4_pity"]
        elif data[0]["guaranteed"] < 0:
            guarantee_change = 0
        else:
            guarantee_change = 1

        if pity_increase == 0:
            pity_increase = -query[0]["tier_5_pity"]

        counted_roll = 0
        if banner["max_rolls"] > 0:
            counted_roll = 1

        await self.bot.db.query(
            """
            INSERT INTO necrobot.Pity(user_id, banner_id, tier_5_pity) VALUES($1, $2, $3) 
            ON CONFLICT (user_id, banner_id) DO
            UPDATE SET 
                tier_5_pity = necrobot.Pity.tier_5_pity + $3, 
                tier_4_pity = necrobot.Pity.tier_4_pity + $4,
                roll_count = necrobot.Pity.roll_count + $5""",
            ctx.author.id,
            banner["id"],
            pity_increase,
            guarantee_change,
            counted_roll,
        )

    @gacha_roll.command(name="cost")
    @has_perms(4)
    async def gacha_roll_cost(self, ctx: commands.Context[NecroBot], amount: int):
        """Change the cost of rolling for a single character, must be at least 1. Default
        is 50.

        {usage}

        __Examples__
        `{pre}gacha roll cost 200` - change the cost of rolling to 200 per roll.
        """
        if amount < 1:
            raise BotError("Please specify a value of at least 1")

        await self.bot.db.query(
            "UPDATE necrobot.FlowersGuild SET roll_cost = $1 WHERE guild_id = $2",
            amount,
            ctx.guild.id,
        )
        await ctx.send(f":white_check_mark: | Updated roll cost to **{amount}**")

    @gacha_roll.command(name="guarantee")
    @has_perms(4)
    async def gacha_roll_guarantee(self, ctx: commands.Context[NecroBot], amount: int):
        """Change the number of rolls it takes to guarantee a 4 or 3 star characters. Set to 0 to never guarantee.

        {usage}

        __Examples__
        `{pre}gacha roll guarantee 5` - On the 5th roll, the roller will be guaranteed a characters.
        """
        if amount < 0:
            raise BotError("Please specify a value of at least 0")

        await self.bot.db.query(
            "UPDATE necrobot.FlowersGuild SET guaranteed = $1 WHERE guild_id = $2",
            amount - 1,
            ctx.guild.id,
        )
        await ctx.send(f":white_check_mark: | Updated guaranteed to **{amount}**")

    @commands.group()
    async def equipment(self, ctx: commands.Context[NecroBot]):
        """{usage}"""
        pass

    @equipment.command(name="equip")
    async def equipment_equip(
        self,
        ctx: commands.Context[NecroBot],
        character: GachaCharacterConverter(allowed_types=("character",), is_owned=True),
        *equipments: GachaCharacterConverter(allowed_types=("weapon", "artefact"), is_owned=True),
    ):
        """Equip a character you own with weapons or artefacts.

        {usage}

        __Examples__
        `{pre}equipment equip Amelan Sword` - Equip Amelan with the weapon Sword.
        """
        if len(equipments) > 2:
            raise BotError("Please specify one weapon and one artefact")

        mapped = {x["type"]: x for x in equipments}

        try:
            if len(equipments) == 2:
                view = Confirm(ctx.author, confirm_msg=None)
                view.message = await ctx.send(
                    "With the new equipment the character will have the following stats:",
                    embed=self.embed_equipment_set(
                        character["name"],
                        EquipmentSet(character, mapped["weapon"], mapped["artefact"]),
                    ),
                    view=view,
                )

                await view.wait()
                if not view.value:
                    return

                await self.bot.db.query(
                    f"""
                    INSERT INTO necrobot.EquipmentSet(guild_id, user_id, char_id, artefact_id, weapon_id) VALUES($1, $2, $3, $4, $5) 
                    ON CONFLICT (guild_id, user_id, char_id)
                    DO UPDATE SET artefact_id = $4, weapon_id = $5""",
                    ctx.guild.id,
                    ctx.author.id,
                    character["id"],
                    mapped["artefact"]["id"],
                    mapped["weapon"]["id"],
                )
                await ctx.send(
                    f":white_check_mark: | Equipped **{character['name']}** with artefact **{mapped['artefact']['name']}** and weapon **{mapped['weapon']['name']}**"
                )
            else:
                key = list(mapped.keys())[0]
                current_equipment = (
                    await self.get_equipment_set(ctx.guild.id, ctx.author.id, (character["id"],))
                )[0]
                if not current_equipment:
                    raise BotError(
                        "Cannot change just one equipment of a character with none. Start by specifying both a weapon and artefact."
                    )

                current_equipment = current_equipment._replace(**{key: mapped[key]})

                view = Confirm(ctx.author, confirm_msg=None)
                view.message = await ctx.send(
                    "With the new equipment the character will have the following stats:",
                    embed=self.embed_equipment_set(
                        current_equipment.character["name"], current_equipment
                    ),
                    view=view,
                )

                await view.wait()
                if not view.value:
                    return

                await self.bot.db.query(
                    f"UPDATE necrobot.EquipmentSet SET {key}_id = $1 WHERE guild_id = $2 AND user_id = $3 AND char_id = $4",
                    mapped[key]["id"],
                    ctx.guild.id,
                    ctx.author.id,
                    character["id"],
                    fetchval=True,
                )

                await ctx.send(
                    f":white_check_mark: | Equipped **{character['name']}** with {key} **{mapped[key]['name']}**"
                )

        except DatabaseError as e:
            raise BotError(
                f"You cannot equip the same weapon/artefact to multiple characters."
            ) from e

    @equipment.command(name="remove")
    async def equipment_remove(
        self, ctx: commands.Context[NecroBot], character: GachaCharacterConverter(allowed_types=("character",), is_owned=True)
    ):
        """Remove the equipment set of a character so that it can be given to another character.

        {usage}
        """
        deleted = await self.bot.db.query(
            "DELETE FROM necrobot.EquipmentSet WHERE user_id = $1 AND guild_id = $2 AND char_id = $3 RETURNING char_id",
            ctx.author.id,
            ctx.guild.id,
            character["id"],
            fetchval=True,
        )
        if not deleted:
            raise BotError(f"Character {character['name']} has no equipment set")

        await ctx.send(f":white_check_mark: | Deleted equipment set for **{character['name']}**")

    def format_character_stats(self, character):
        stats = f"- Health: {self.c(character['primary_health'])} ({self.c(character['secondary_health'])})\n- PA: {self.c(character['physical_attack'])}\n- MA: {self.c(character['magical_attack'])}\n- PD: {self.c(character['physical_defense'])}\n- MD: {self.c(character['magical_defense'])}"
        return f"- Name: {character['name']}\n- Tier: {character['tier'] * ':star:'}\n\n__Stats__\n{stats}"

    async def get_equipment_set(self, guild_id, user_id, character_ids=()) -> List[EquipmentSet]:
        string = f"""
            SELECT c1.*, ':', c2.*, ':', c3.* as artefact
            FROM necrobot.EquipmentSet as es
                JOIN necrobot.Characters as c1 ON es.char_id = c1.id 
                JOIN necrobot.Characters as c2 ON es.weapon_id = c2.id 
                JOIN necrobot.Characters as c3 ON es.artefact_id = c3.id
            WHERE guild_id = $1 AND user_id = $2{' AND c1.id = ANY($3)' if character_ids else ''};"""

        if character_ids:
            query = await self.bot.db.query(string, guild_id, user_id, character_ids)
        else:
            query = await self.bot.db.query(string, guild_id, user_id)

        return [
            EquipmentSet(
                *[
                    {key: value for key, value in y}
                    for x, y in itertools.groupby(entry.items(), lambda z: z[1] == ":")
                    if not x
                ]
            )
            for entry in query
        ]

    def embed_equipment_set(self, name, entry: EquipmentSet):
        character = Character(
            name=entry.character["name"],
            stats=StatBlock.from_dict(entry.character),
            weapon=StattedEntity(
                name=entry.weapon["name"], stats=StatBlock.from_dict(entry.weapon)
            ),
            artefact=StattedEntity(
                name=entry.artefact["name"], stats=StatBlock.from_dict(entry.artefact)
            ),
        )

        embed = discord.Embed(
            title=name,
            colour=self.bot.bot_color,
            description=f"- Character: {entry.character['name']} ({entry.character['tier'] * ':star:'})\n- Weapon: {entry.weapon['name']} ({entry.weapon['tier'] * ':star:'})\n- Artefact: {entry.artefact['name']} ({entry.artefact['tier'] * ':star:'})",
        )
        embed.set_footer(**self.bot.bot_footer)

        stats = f"- Health: {self.c(character.calculate_stat('primary_health'))} ({self.c(character.calculate_stat('secondary_health'))})\n- PA: {self.c(character.calculate_stat('physical_attack'))}\n- MA: {self.c(character.calculate_stat('magical_attack'))}\n- PD: {self.c(character.calculate_stat('physical_defense'))}\n- MD: {self.c(character.calculate_stat('magical_defense'))}"
        embed.add_field(name="Stats", value=stats, inline=False)

        active_skill = get_skill(entry.character["active_skill"])
        if active_skill is not None:
            embed.add_field(
                name=f"Active: {active_skill.name}",
                value=f"{active_skill.description}\n- Cooldown: {active_skill.cooldown} turns",
            )

        passive_skill = get_skill(entry.character["passive_skill"])
        if passive_skill is not None:
            embed.add_field(name=f"Passive: {passive_skill.name}", value=passive_skill.description)

        return embed

    @equipment.command(name="list")
    async def equipment_list(self, ctx: commands.Context[NecroBot]):
        """List your characters and their equipment.

        {usage}

        __Examples
        `{pre}equipment list` - list all your equipped characters"""

        def embed_maker(view, entry):
            return self.embed_equipment_set(
                f"{entry.character['name']} ({view.page_number}/{view.page_count})", entry
            )

        entries = await self.get_equipment_set(ctx.guild.id, ctx.author.id)
        await paginate(ctx, entries, 1, embed_maker)

    def convert_battlefield_to_str(
        self, field: Battlefield, characters: List[Character], character_range: Character = None
    ):
        character_reach = []
        grid = Grid(matrix=field.walkable_grid([x.position for x in characters]))

        if character_range is not None:
            character_reach.append(grid.node(*character_range.position))
            for _ in range(character_range.current_movement_range):
                new_neighbors = []
                for node in character_reach:
                    new_neighbors.extend(grid.neighbors(node))
                character_reach.extend(new_neighbors)

        empty_board = []
        for y, row in enumerate(field.tiles):
            empty_row = []
            for x, cell in enumerate(row):
                if is_wakable(cell):
                    in_range = grid.node(x, y) in character_reach
                    if in_range:
                        empty_row.append(":blue_square:")
                    else:
                        empty_row.append(":black_large_square:")
                else:
                    empty_row.append(":red_square:")
            empty_board.append(empty_row)

        for character in characters:
            empty_board[character.position[1]][character.position[0]] = POSITION_EMOJIS[
                character.index
            ]

        return "\n".join(["".join(row) for row in empty_board])

    def embed_battle(self, battle: Battle, *, character_range: Character = None, page: int = 0):
        embed = discord.Embed(
            title="A Great Battle",
            colour=self.bot.bot_color,
            description=self.convert_battlefield_to_str(
                battle.battlefield, battle.players + battle.enemies, character_range
            ),
        )

        embed.set_footer(**self.bot.bot_footer)

        if page == 0:
            for entity_name, entities in (
                ("Players", battle.players),
                ("Enemies", battle.enemies),
            ):
                embed.add_field(
                    name=entity_name,
                    value="\n".join(
                        f"{POSITION_EMOJIS[character.index]} - **{character.name}**: {character.stats.current_primary_health}/{character.stats.max_primary_health} ({character.stats.current_secondary_health}/{character.stats.max_secondary_health})"
                        for character in entities
                    ),
                )

            embed.add_field(
                name="Actions",
                value="\n".join(
                    map(
                        str,
                        reversed(
                            (
                                (
                                    ["\N{BLACK CIRCLE FOR RECORD}\N{VARIATION SELECTOR-16} -"]
                                    * LOG_SIZE
                                )
                                + battle.action_logs
                            )[-LOG_SIZE:]
                        ),
                    )
                ),
                inline=False,
            )
            embed.add_field(
                name="Key",
                value=":blue_square: - possible movement\n:black_medium_square: - walkable terrain\n:red_square: - impassable terrain",
            )
        else:
            character = battle.players[page - 1]

            modifiers = ", ".join(
                (f"{modifier.name} ({modifier.duration})" for modifier in character.modifiers)
            )
            string = (
                f"- Symbol: {POSITION_EMOJIS[character.index]} \n"
                f"- Health: {character.stats.current_primary_health}/{character.stats.max_primary_health} ({character.stats.current_secondary_health}/{character.stats.max_secondary_health}) \n"
                f"- Modifiers: {modifiers}\n"
                f"- PA: {self.c(character.calculate_stat('physical_attack'))}\n"
                f"- MA: {self.c(character.calculate_stat('magical_attack'))}\n"
                f"- PD: {self.c(character.calculate_stat('physical_defense'))}\n"
                f"- MD: {self.c(character.calculate_stat('magical_defense'))}"
            )
            embed.add_field(name=character.name, value=string)

        return embed

    @gacha.command(name="battle")
    async def gacha_battle(
        self, ctx: commands.Context[NecroBot], *chars: GachaCharacterConverter(allowed_types=("character",), is_owned=True)
    ):
        if len(chars) != 3:
            raise BotError("Please submit exactly three characters for the battle.")

        equipment_sets = await self.get_equipment_set(
            ctx.guild.id, ctx.author.id, [char["id"] for char in chars]
        )
        if len(equipment_sets) != 3:
            raise BotError("Please submit characters with valid equipment sets.")

        characters = [
            Character(
                name=es.character["name"],
                stats=StatBlock.from_dict(es.character),
                weapon=StattedEntity(name=es.weapon["name"], stats=StatBlock.from_dict(es.weapon)),
                artefact=StattedEntity(
                    name=es.artefact["name"], stats=StatBlock.from_dict(es.artefact)
                ),
                active_skill=get_skill(es.character["active_skill"]),
                passive_skill=get_skill(es.character["passive_skill"]),
            )
            for es in equipment_sets
        ]

        # field = copy.deepcopy(random.choice(POTENTIAL_FIELDS))
        field = copy.deepcopy(POTENTIAL_FIELDS[1])
        enemies = [
            copy.deepcopy(random.choice(POTENTIAL_ENEMIES)) for _ in range(field.enemy_count)
        ]
        battle = Battle(
            characters,
            enemies,
            field,
        )
        battle.initialise()

        cmd = CombatView(battle, self.embed_battle, ctx.author)
        cmd.message = await ctx.send(embed=self.embed_battle(battle), view=cmd)

        await cmd.wait()

        cmd.clear_items()
        if cmd.victory:
            await cmd.message.edit(content="The battle ended in victory", view=cmd)
        else:
            await cmd.message.edit(content="The battle ended in defeat", view=cmd)

    #######################################################################
    ## Events
    #######################################################################

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id in self.bot.settings["blacklist"]:
            return

        if payload.emoji.name == "\N{CHERRY BLOSSOM}" and payload.message_id in self.bot.events:
            if payload.user_id in self.bot.events[payload.message_id]["users"]:
                return

            self.bot.events[payload.message_id]["users"].append(payload.user_id)
            await self.add_flowers(
                payload.guild_id,
                payload.user_id,
                self.bot.events[payload.message_id]["amount"],
            )
