import asyncio
import json
import math
import random
import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from rings.db import DatabaseError

from rings.utils.checks import has_perms
from rings.utils.ui import Confirm, paginate
from rings.utils.utils import check_channel, BotError 
from rings.utils.converters import FlowerConverter, GachaBannerConverter, GachaCharacterConverter, TimeConverter

from typing import Literal, Union

"""
{
        "name": "",
        "image_url": "",
        "description": "",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
"""


DUD_TEMPLATES = [
    {
        "name": "Bag of Goodies",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116482199466819695/HReach-HealthPack.png",
        "description": "A bag containing some goodies, good to eat but not for much else.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Ancient Blade",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116707849876275260/462px-Weapon_b_1020002200.png",
        "description": "An old sword, very finely crafted but dulled by time.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Broken Hourglass",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116718269496299520/desktop-wallpaper-fantasy-artistic-video-game-sand-clock.png",
        "description": "This hourglass used to be able to tell the time with no equal but evert since the glass was shattered it has been abandoned.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Shattered Crown",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116797755659128923/Broken_Crown_icon.png",
        "description": "The crown of the empress of an long forgotten empire. It is said she wore it till she was betrayed by her own knights. The killing blow shattered the crown and doomed the kingdom.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Rusty Goblet",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116799230338662480/public.png",
        "description": "This goblet sat on the table of the many kings of an ancient realm before it fell to the forces of evil.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "The Twin Dragons",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116800827185696778/latest.png",
        "description": "A dirty medallion, long ago it held power of life itself. Roughly welded together, the pieces were used in a dark ritual before being discarded.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Tablets of the Arbiter",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116814455829971148/latest.png",
        "description": "An ancient tablet, a powerful tool used by the Arbiter to defeat his enemies. Now, long after his death, it is just a shattered pile of stone.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Splintered Síoraíocht",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116816978523455498/636284768481526959.png",
        "description": "The flame staff was once a symbol of power of an entire civilisation, it was taken away when that civilisation fell in a fool hope. Now its owner lays dead and the staff has been splintered.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Extinguished Silverlight",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1117099808822407268/glass_weapon_7_by_rittik_designs-d895tzq.png",
        "description": "Once the blade of a powerful king, its light faded when the great darkness swept over the land, the likes of it never to be again.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Thawed Frostpear",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1117116745736523827/Select20a20file20name20for20output20files_004.png",
        "description": "This wet spear was once a great frost spear, wielded by the mightiest of Dragon-knights. Bathed in demonic flames during the Cataclysm, its icy point thawed and its power was undone.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Failnaught",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1117182929311899789/latest.png",
        "description": "A dull, unstrung bow. Age has faded the ornate painting on the wood and rendered it brittle. ",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
]


class Flowers(commands.Cog):
    """A server specific economy system. Use it to reward/punish users at you heart's content. Also contains a gacha system."""

    def __init__(self, bot):
        self.bot = bot

        self.DUD_PERCENT = 0.33

    #######################################################################
    ## Cog Functions
    #######################################################################

    def cog_check(self, ctx : commands.Context):
        if ctx.guild:
            return True

        raise commands.CheckFailure("This command cannot be used in private messages.")

    #######################################################################
    ## Functions
    #######################################################################

    async def add_flowers(self, guild_id, user_id, amount):
        await self.bot.db.query(
            "UPDATE necrobot.Flowers SET flowers = flowers + $3 WHERE guild_id=$1 AND user_id=$2",
            guild_id,
            user_id,
            amount,
        )

    async def transfer_flowers(self, guild_id, payer, payee, amount):
        await self.add_flowers(guild_id, payer, -amount)
        await self.add_flowers(guild_id, payee, amount)

    async def get_flowers(self, guild_id, user_id):
        flowers = await self.bot.db.query(
            "SELECT flowers FROM necrobot.Flowers WHERE guild_id=$1 AND user_id=$2",
            guild_id,
            user_id,
        )

        return flowers[0][0]

    async def get_symbol(self, guild_id):
        symbol = await self.bot.db.query(
            "SELECT symbol FROM necrobot.FlowersGuild WHERE guild_id=$1", guild_id
        )

        return symbol[0][0]

    async def update_symbol(self, guild_id, symbol):
        await self.bot.db.query(
            "UPDATE necrobot.FlowersGuild SET symbol=$2 WHERE guild_id=$1",
            guild_id,
            symbol,
        )

    async def get_balance(self, ctx, user):
        if user is None:
            user = ctx.author

        flowers = await self.get_flowers(ctx.guild.id, user.id)
        symbol = await self.get_symbol(ctx.guild.id)

        await ctx.send(f":atm: | {user.name} has **{flowers}** {symbol}")

    async def add_characters_to_user(self, guild_id, user_id, char_id):
        query = await self.bot.db.query("""
            INSERT INTO necrobot.RolledCharacters(guild_id, user_id, char_id) VALUES($1, $2, $3)
            ON CONFLICT (guild_id, user_id, char_id)
            DO UPDATE SET level = RolledCharacters.level + 1 RETURNING RolledCharacters.level;
        """, guild_id, user_id, char_id, fetchval=True)
        
        return query
    
    async def remove_character_from_user(self, guild_id, user_id, char_id, amount):
        conn = await self.bot.db.get_conn()
        async with conn.transaction():
            level = await self.bot.db.query(
                "UPDATE necrobot.RolledCharacters SET level = level - $4 WHERE guild_id = $1 AND user_id=$2 AND char_id=$3 RETURNING level;",
                guild_id, user_id, char_id, amount, fetchval=True
            )

            deleted = await self.bot.db.query(
                "DELETE FROM necrobot.RolledCharacters WHERE guild_id = $1 AND user_id=$2 AND char_id=$3 AND level < 1 RETURNING char_id;",
                guild_id, user_id, char_id, fetchval=True
            )

        return level, deleted
    
    def convert_exp_to_level(self, exp, tier):
        level = 0
        thresholds = [
            1,
            3,
            5,
            7,
            10,
        ]

        for threshold in thresholds:
            true_threshold = (5 - threshold) * tier // 2
            if exp >= true_threshold:
                level += 1
                exp -= true_threshold
            else:
                break
        else:
            true_threshold = 0

        return level, exp, true_threshold
    
    def calculate_weight(self, tier, modifier, pity):
        weight = ( 2 ** ( 1 + ( 5 - tier ) ) ) * modifier

        if tier != 5:
            return weight
        
        pity_pass = random.choices([False, True], [60, pity])
        if pity_pass[0]:
            weight = weight + max(0, pity - 30)

        return weight
    
    def embed_character(self, character, admin=False):
        embed = discord.Embed(
            title=character["name"],
            colour=self.bot.bot_color,
            description=character['description'],
        )

        if character.get("image_url"):
            embed.set_image(url=character["image_url"])

        embed.set_footer(**self.bot.bot_footer)

        if character.get("id"):
            embed.add_field(name="ID", value=character["id"])
    
        embed.add_field(name="Title", value=character["title"])
        embed.add_field(name="Tier", value=f"{character['tier']*':star:' if character['tier'] else ':fleur_de_lis:'}")
        embed.add_field(name="Universe", value=character["universe"])
    
        if character.get("level"):
            level, exp, next_threshold = self.convert_exp_to_level(character["level"], character["tier"])
            embed.add_field(name="Level", value=f"{level} ({exp}/{next_threshold})")

        if admin and character.get("obtainable"):
            embed.add_field(name="Obtainable", value=character["obtainable"])

        if character.get("total"):
            embed.add_field(name="Count", value=character["total"])

        return embed
    
    def embed_banner(self, banner, admin=False):
        embed = discord.Embed(
            title=f"{banner['name']}",
            colour=self.bot.bot_color,
            description=banner['description'],
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
            embed.add_field(name="Max Rolls", value=banner["max_rolls"] if banner["max_rolls"] > 0 else "No max")

        return embed
    
    async def pay_for_roll(self, guild_id, user_id, cost):
        await self.bot.db.query("""
            UPDATE necrobot.Flowers SET flowers = flowers - $3 WHERE user_id = $2 AND guild_id = $1""", 
            guild_id, user_id, cost
        )

    async def get_characters(self):
        return await self.bot.db.query("""
            SELECT id, name, title, tier, universe, description, image_url, obtainable, count(rolled.char_id) as total 
            FROM necrobot.Characters as chars
            LEFT JOIN necrobot.RolledCharacters as rolled on chars.id = rolled.char_id
            GROUP BY chars.id
            ORDER BY universe ASC, name ASC
        """)
    
    def pull(self, characters, pity = 0, guarantee = False):
        duds = [random.choice(DUD_TEMPLATES) for _ in range(math.ceil(len(characters) * self.DUD_PERCENT))]
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
        self, ctx : commands.Context, member: discord.Member, amount: int, *, reason: str = None
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
    async def flowers_symbol(self, ctx : commands.Context, symbol: str):
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
    async def flowers_balance(self, ctx : commands.Context, user: discord.Member = None):
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
        ctx,
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
        msg = await channel.send(embed=embed, delete_after=time)
        await msg.add_reaction("\N{CHERRY BLOSSOM}")
        self.bot.events[msg.id] = {"users": [], "amount": amount}

    @commands.command()
    @commands.guild_only()
    async def give(self, ctx : commands.Context, member: discord.Member, amount: FlowerConverter):
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
    async def characters(self, ctx, for_banner: bool = False):
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
    async def characters_list(self, ctx):
        """Compact list of characters
        
        {usage}
        
        __Examples__
        `{pre}characters list` - list characters
        """
        characters = await self.get_characters()

        def embed_maker(view, entries):
            description = "\n".join([f"- {entry['id']} - {entry['name']} ({entry['universe']}): **{entry['tier']}**:star:" for entry in entries])
            embed = discord.Embed(
                title=f"Character List ({view.page_number}/{view.page_count})",
                colour=self.bot.bot_color,
                description=description,
            )
            embed.set_footer(**self.bot.bot_footer)

            return embed

        await paginate(ctx, characters, 10, embed_maker)

    @characters.command(name="get")
    async def characters_list(self, ctx, character: GachaCharacterConverter):
        """Get info on a specific character.
        
        {usage}
        
        __Example__
        `{pre}characters get Amelan` - get info on the character called Amelan.
        """
        await ctx.send(embed=self.embed_character(character, True))

    @characters.command(name="create")
    @has_perms(6)
    async def characters_create(self, ctx, name: str, title: str, universe: str, tier: int):
        """Add a new character 
        
        {usage}
        
        __Examples__
        `{pre}characters create "John" "The Destroyer" "Rift" "2"` - Start the creation process.
        """
        description = None
        image = None
        char_id = None

        def general_check(m):
            if not m.author == ctx.author or not m.channel == ctx.channel:
                return False

            if m.content.lower() == "exit":
                raise BotError("Exited setup")

            return True

        def embed_maker():
            return self.embed_character({
                "name": name,
                "description": description,
                "image_url": image,
                "title": title,
                "tier": tier,
                "universe": universe,
                "obtainable": False,
                "id": char_id
            })

        msg = await ctx.send("Let's get started", embed=embed_maker())

        await ctx.send("Post a description of the character. Type exit to cancel.")
        start_m = await self.bot.wait_for("message", check=general_check, timeout=300)
        description = start_m.content.strip()
        await msg.edit(embed=embed_maker())

        await ctx.send("Post a image url or upload an image of the character. If you upload the image do not delete it after. Type exit to cancel.")
        start_m = await self.bot.wait_for("message", check=general_check, timeout=300)
        if start_m.attachments:
            image = start_m.attachments[0].url
        else:
            image = start_m.content.strip()
    
        try:
            await msg.edit(embed=embed_maker())
        except Exception as e:
            raise BotError(f"Something went wrong while adding the image: {e}") from e

        view = Confirm(confirm_msg=":white_check_mark: | Character created, toggle it to make it obtainable.")
        view.message = await ctx.send(
            f"Are you satifised with your character?",
            view=view,
        )
        await view.wait()
        if not view.value:
            return
        
        char_id = await self.bot.db.query(
            "INSERT INTO necrobot.Characters(name, title, description, image_url, tier, obtainable, universe) VALUES($1, $2, $3, $4, $5, $6, $7) RETURNING id",
            name, title, description, image, tier, False, universe, fetchval=True
        )

        await msg.edit(embed=embed_maker())

    @characters.command(name="edit")
    @has_perms(6)
    async def characters_edit(self, ctx, char: GachaCharacterConverter, field: Literal["name", "description", "title", "image_url", "universe", "tier"], *, value: str):
        """Edit a character's value
        
        {usage}
        
        __Example__
        `{pre}characters edit Amelan title Big Boy` - Edit Amelan's title to "Big Boy"
        """
        await self.bot.db.query(f"UPDATE necrobot.Characters SET {field} = $1 WHERE id = $2", value, char["id"])
        await ctx.send(f":white_check_mark: | Field {field} for character **{char['name']}** updated")

    @characters.command(name="delete")
    @has_perms(6)
    async def characters_delete(self, ctx, char: GachaCharacterConverter):
        """Delete a character and remove them from all player's accounts
        
        {usage}
        
        __Examples__
        `{pre}characters delete 12141` - Delete the character
        """
        query = await self.bot.db.query("DELETE FROM necrobot.Characters WHERE id=$1 RETURNING name;", char["id"], fetchval=True)
        await ctx.send(f":white_check_mark: | Character **{query[0]}** deleted and removed.")

    @characters.command(name="toggle")
    @has_perms(6)
    async def characters_toggle(self, ctx, char: GachaCharacterConverter):
        """Toggle whether or not a character can be obtained as part of a banner
        
        {usage}
        
        __Examples__
        `{pre}characters toggle 12141` - Toggle a character
        """
        query = await self.bot.db.query("UPDATE necrobot.Characters SET obtainable=not obtainable WHERE id=$1 RETURNING (name, obtainable);", char["id"], fetchval=True)
        await ctx.send(f":white_check_mark: | Character **{query[0]}** is now {'not ' if not query[1] else ''}obtainable.")

    @characters.command(name="give")
    @has_perms(4)
    async def characters_give(self, ctx, user: discord.Member, char: GachaCharacterConverter):
        """Add a level of characte to a player's account
        
        {usage}
        
        __Examples__
        `{pre}characters give @Necro 12141` - Give one level of character 12141 to Necro
        """
        level = await self.add_characters_to_user(ctx.guild.id, user.id, char["id"])
        await ctx.send(f":white_check_mark: | Added character to user's rolled characters (New: {level == 1})")

    @characters.command(name="take")
    @has_perms(4)
    async def characters_take(self, ctx, user: discord.Member, char: GachaCharacterConverter, amount: int = 1):
        """Remove a level of characte to a player's account
        
        {usage}
        
        __Examples__
        `{pre}characters take @Necro 12141` - Remove one level of character 12141 from Necro
        """
        level, is_deleted = await self.remove_character_from_user(ctx.guild.id, user.id, char["id"], amount)
        if not level and not is_deleted:
            await ctx.send(":negative_squared_cross_mark: | User does not have that character")
        else:
            await ctx.send(f":white_check_mark: | Amount taken from user's rolled characters (Deleted: {bool(is_deleted)})")

    
    @commands.group(invoke_without_command=True, aliases=["banner"])
    @commands.guild_only()
    async def banners(self, ctx, archive: bool = False):
        """List ongoing banners
        
        {usage}
        
        __Examples__
        `{pre}characters` - List ongoing banners
        `{pre}characters true` - List all ongoing and ended banners
        """
        if archive:
            banners = await self.bot.db.query("""
                SELECT b.*, json_agg(json_build_array(c.name, c.tier)) as characters FROM necrobot.Banners AS b 
                    JOIN necrobot.BannerCharacters AS bc ON b.id=bc.banner_id 
                    JOIN necrobot.Characters as c ON bc.char_id=c.id
                WHERE guild_id=$1
                group by b.id
            """, ctx.guild.id)
        else:
            banners = await self.bot.db.query("""
                SELECT b.*, json_agg(json_build_array(c.name, c.tier)) as characters FROM necrobot.Banners AS b 
                    JOIN necrobot.BannerCharacters AS bc ON b.id=bc.banner_id 
                    JOIN necrobot.Characters as c ON bc.char_id=c.id
                WHERE guild_id=$1 AND ongoing=true
                group by b.id
            """, ctx.guild.id)


        def embed_maker(view, entry):
            mutable_entry = dict(entry)
            mutable_entry["name"] = f"{entry['name']} ({view.page_number}/{view.page_count})"
            mutable_entry["characters"] = [f"{char[0]} ({char[1]} :star:)" for char in json.loads(entry["characters"])]
            return self.embed_banner(mutable_entry, archive)

        await paginate(ctx, banners, 1, embed_maker)

    @banners.command(name="create")
    @has_perms(4)
    async def banners_create(self, ctx, *, name):
        """Add a new banner in the guild. 
        
        {usage}
        
        __Examples__
        `{pre}banner create Rose Lily Banner` - Start the creation for a banner
        """
        description = None
        image = None
        characters = []
        banner_id = None
        max_rolls = 0

        def general_check(m):
            if not m.author == ctx.author or not m.channel == ctx.channel:
                return False

            if m.content.lower() == "exit":
                raise BotError("Exited setup")

            return True
        
        def number_check(m):
            if not general_check(m):
                return False
            
            argument = m.content.strip()
            if not argument.isdigit():
                return False
            
            argument = int(argument)
            if not argument >= 0:
                return False
            
            return True

        def embed_maker():
            return self.embed_banner({
                "id": banner_id,
                "image_url": image,
                "description": description,
                "characters":  [f"{char['name']} ({char['tier']} :star:)" for char in characters],
                "name": name,
                "max_rolls": max_rolls
            })

        msg = await ctx.send("Let's get started", embed=embed_maker())

        await ctx.send("Post a description of the banner. Type exit to cancel.")
        start_m = await self.bot.wait_for("message", check=general_check, timeout=300)
        description = start_m.content.strip()
        await msg.edit(embed=embed_maker())

        await ctx.send("Post a url for the image of the banner. Type exit to cancel or `NULL` to not have an image.")
        start_m = await self.bot.wait_for("message", check=general_check, timeout=300)
        image = start_m.content.strip()
        if image.lower() == "null":
            image = None
        
        try:
            await msg.edit(embed=embed_maker())
        except Exception as e:
            raise BotError(f"Not a valid image: {e}") from e

        await ctx.send("Post a positive number for the max amount of times a player can roll on this banner. Type exit to cancel or `0` to not have a max roll.")
        start_m = await self.bot.wait_for("message", check=number_check, timeout=300)
        max_rolls = int(start_m.content.strip())
        await msg.edit(embed=embed_maker())

        await ctx.send("Post a comma separated list of characters for the banner. Type exit to cancel.")
        start_m = await self.bot.wait_for("message", check=general_check, timeout=300)
        characters = [await GachaCharacterConverter(True).convert(ctx, x.strip()) for x in start_m.content.split(",")]
        await msg.edit(embed=embed_maker())

        view = Confirm(confirm_msg=":white_check_mark: | Banner created, toggle it to make it ongoing")
        view.message = await ctx.send(
            f"Are you satifised with your banner?",
            view=view,
        )
        await view.wait()
        if not view.value:
            return
        
        banner_id = await self.bot.db.query(
            "INSERT INTO necrobot.Banners(guild_id, name, description, image_url, max_rolls) VALUES($1, $2, $3, $4, $5) RETURNING id",
            ctx.guild.id, name, description, image, max_rolls, fetchval=True
        )

        await self.bot.db.query(
            "INSERT INTO necrobot.BannerCharacters VALUES($1, $2, $3)", 
            [(banner_id, x["id"], 1) for x in characters], many=True
        )
        
        await msg.edit(embed=embed_maker())

    @banners.command(name="toggle")
    @has_perms(4)
    async def banners_toggle(self, ctx, banner : GachaBannerConverter(False)):
        """Toggle whether or not a banner is currently running
        
        {usage}
        
        __Examples__
        `{pre}banner toggle 12141` - Toggle a banner
        """
        query = await self.bot.db.query("UPDATE necrobot.Banners SET ongoing=not ongoing WHERE id=$1 RETURNING (name, ongoing);", banner["id"], fetchval=True)
        await ctx.send(f":white_check_mark: | Banner **{query[0]}** is now {'not ' if not query[1] else ''}ongoing.")

    @banners.command(name="add")
    @has_perms(4)
    async def banners_add(self, ctx, banner: GachaBannerConverter(False), *, char : GachaCharacterConverter):
        """Add characters to a banner
        
        {usage}
        
        __Examples__
        `{pre}banners add 12141 John the Smith` - add character John to the banner
        """
        try:
            await self.bot.db.query("""
                INSERT INTO necrobot.BannerCharacters(banner_id, char_id) VALUES($1, $2)
                """, banner["id"], char["id"]
            )
            await ctx.send(f":white_check_mark: | Character **{char['name']}** added to banner **{banner['name']}**.")
        except DatabaseError:
            await ctx.send(f":negative_squared_cross_mark: | Character **{char['name']}** already in banner **{banner['name']}**.")

    @banners.command(name="remove")
    @has_perms(4)
    async def banners_remove(self, ctx, banner: GachaBannerConverter(False), *, char : GachaCharacterConverter):
        """Remove characters from a banner
        
        {usage}
        
        __Examples__
        `{pre}banners remove 12141 John the Smith` - remove character John from the banner
        """
        is_deleted = await self.bot.db.query("""
            DELETE FROM necrobot.BannerCharacters WHERE banner_id = $1 AND char_id = $2 RETURNING char_id
            """, banner["id"], char["id"]
        )

        if is_deleted:
            await ctx.send(f":white_check_mark: | Characters **{char['name']}** removed from banner **{banner['name']}**.")
        else:
            await ctx.send(f":negative_squared_cross_mark: | Characters **{char['name']}** not present on banner **{banner['name']}**.")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def gacha(self, ctx):
        """Get information on the gacha on this server
        
        {usage}
        
        __Examples__
        `{pre}gacha` - get information on the gacha in this server
        """
        guild = await self.bot.db.query("SELECT roll_cost, symbol, guaranteed FROM necrobot.FlowersGuild WHERE guild_id = $1", ctx.guild.id)
        if guild[0]["guaranteed"] >= 0:
            guarantee = f"You are guaranteed a character after **{guild[0]['guaranteed'] + 1}** rolls."
        else:
            guarantee = "You are not guaranteed a character after any amount of rolls."

        await ctx.send(f":game_die: | A roll on this server costs **{guild[0]['roll_cost']}** {guild[0]['symbol']}.\n:star2: | {guarantee}")

    @gacha.command(name="balance")
    @commands.guild_only()
    async def gacha_balance(self, ctx : commands.Context, user : discord.Member = None):
        """Check your or a user's balance of flowers

        {usage}

        __Examples__
        `{pre}$` - check you own balance
        `{pre}$ @Necro` - check the user Necro's balance
        """
        await self.get_balance(ctx, user)

    @gacha.command(name="characters", aliases=["char", "character"])
    @commands.guild_only()
    async def gacha_characters(self, ctx):
        """List all your characters and their info.
        
        {usage}
        
        __Examples__
        `{pre}gacha char` - List your characters"""
        characters = await self.bot.db.query("""
            SELECT c.*, rc.level FROM necrobot.RolledCharacters as rc 
                JOIN necrobot.Characters as c ON rc.char_id = c.id 
            WHERE rc.guild_id = $1 AND rc.user_id = $2
            ORDER BY c.universe, c.name""", 
            ctx.guild.id, ctx.author.id
        )

        def embed_maker(view, entry):
            mutable_entry = dict(entry)
            mutable_entry["name"] = f"{entry['name']} ({view.page_number}/{view.page_count})"
            return self.embed_character(mutable_entry)

        await paginate(ctx, characters, 1, embed_maker)

    @gacha.group(name="roll", invoke_without_command=True, aliases=["pull"])
    @commands.guild_only()
    @commands.max_concurrency(1, per=BucketType.user, wait=True)
    async def gacha_roll(self, ctx, *, banner : GachaBannerConverter):
        pity = 0
        guarantee = False
        roll_count = 0

        query = await self.bot.db.query("SELECT tier_5_pity, tier_4_pity, roll_count FROM necrobot.Pity WHERE user_id = $1 AND banner_id = $2", ctx.author.id, banner["id"])
        data = await self.bot.db.query("SELECT symbol, roll_cost, guaranteed FROM necrobot.FlowersGuild WHERE guild_id = $1", ctx.guild.id)
        
        if query:
            pity = query[0]["tier_5_pity"]
            guarantee = query[0]["tier_4_pity"] >= data[0]["guaranteed"] and data[0]["guaranteed"] >= 0
            roll_count = query[0]["roll_count"]            

        if banner["max_rolls"] > 0 and roll_count >= banner["max_rolls"]:
            raise BotError("You've hit the max amount of rolls on this banner.")


        characters = await self.bot.db.query("""
            SELECT c.*, bc.modifier FROM necrobot.BannerCharacters as bc 
                JOIN necrobot.Characters as c ON bc.char_id = c.id 
            WHERE bc.banner_id = $1
            ORDER BY c.universe, c.name""", 
            banner["id"]
        )

        mutable_banner = dict(banner)
        mutable_banner["characters"] = [f"{char['name']} ({char['tier']} :star:)" for char in characters]

        view = Confirm(confirm_msg=None)
        view.message = await ctx.send(f"Roll on this banner for **{data[0]['roll_cost']}** {data[0]['symbol']}?", embed=self.embed_banner(mutable_banner), view=view)
        await view.wait()
        if not view.value:
            return

        try:
            await self.pay_for_roll(ctx.guild.id, ctx.author.id, data[0]["roll_cost"])
        except DatabaseError as e:
            raise BotError("You no longer have enough flowers for a pull.") from e

        pulled_char, guaranteed = self.pull(characters, pity, guarantee)

        sleep = 5
        if pulled_char["tier"] == 5:
            pity_increase = -1
            pull_animation = "https://media.tenor.com/rOuL0G1uRpMAAAAd/genshin-impact-pull.gif"
        elif pulled_char["tier"] == 4:
            pity_increase = 3
            pull_animation = "https://media.tenor.com/pVzBgcp1RPQAAAAd/genshin-impact-animation.gif"
        else:
            sleep = 2
            pity_increase = 2
            pull_animation = "https://media.tenor.com/-0gPdn6GMVAAAAAC/genshin3star-wish.gif"

        if pulled_char.get("id"): #not a dud
            level = await self.add_characters_to_user(ctx.guild.id, ctx.author.id, pulled_char["id"])
            pulled_char["level"] = level
        else:
            pity = 1

        await asyncio.sleep(0.5)
        await view.message.edit(embed=discord.Embed().set_image(url=pull_animation))
        await asyncio.sleep(sleep)
        await view.message.edit(content=f":game_die: | You payed **{data[0]['roll_cost']}** {data[0]['symbol']} and got the following reward:", embed=self.embed_character(pulled_char))

        if guaranteed:
            guarantee_change = -query[0]["tier_4_pity"]
        elif pulled_char["tier"] == 3 or data[0]["guaranteed"] < 0:
            guarantee_change = 0
        else:
            guarantee_change = 1
        
        if pity_increase == 0:
            pity_increase = -query[0]["tier_5_pity"]

        counted_roll = 0
        if banner["max_rolls"] > 0:
            counted_roll = 1
        
        await self.bot.db.query("""
            INSERT INTO necrobot.Pity(user_id, banner_id, tier_5_pity) VALUES($1, $2, $3) 
            ON CONFLICT (user_id, banner_id) DO
            UPDATE SET 
                tier_5_pity = necrobot.Pity.tier_5_pity + $3, 
                tier_4_pity = necrobot.Pity.tier_4_pity + $4,
                roll_count = necrobot.Pity.roll_count + $5""", 
            ctx.author.id, banner["id"], pity_increase, guarantee_change, counted_roll
        )

    @gacha_roll.command(name="cost")
    @has_perms(4)
    async def gacha_roll_cost(self, ctx, amount: int):
        """Change the cost of rolling for a single character, must be at least 1. Default
        is 50.
        
        {usage}
        
        __Examples__
        `{pre}gacha roll cost 200` - change the cost of rolling to 200 per roll.
        """
        if amount < 1:
            raise BotError("Please specify a value of at least 1")

        await self.bot.db.query("UPDATE necrobot.FlowersGuild SET roll_cost = $1 WHERE guild_id = $2", amount, ctx.guild.id)
        await ctx.send(f":white_check_mark: | Updated roll cost to **{amount}**")

    @gacha_roll.command(name="guarantee")
    @has_perms(4)
    async def gacha_roll_guarantee(self, ctx, amount: int):
        """Change the number of rolls it takes to guarantee a 4 or 3 star characters. Set to 0 to never guarantee.
        
        {usage}
        
        __Examples__
        `{pre}gacha roll guarantee 5` - On the 5th roll, the roller will be guaranteed a characters.
        """
        if amount < 0:
            raise BotError("Please specify a value of at least 0")

        await self.bot.db.query("UPDATE necrobot.FlowersGuild SET guaranteed = $1 WHERE guild_id = $2", amount-1, ctx.guild.id)
        await ctx.send(f":white_check_mark: | Updated guaranteed to **{amount}**")

    #######################################################################
    ## Events
    #######################################################################

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id in self.bot.settings["blacklist"]:
            return

        if (
            payload.emoji.name == "\N{CHERRY BLOSSOM}"
            and payload.message_id in self.bot.events
        ):
            if payload.user_id in self.bot.events[payload.message_id]["users"]:
                return

            self.bot.events[payload.message_id]["users"].append(payload.user_id)
            await self.add_flowers(
                payload.guild_id,
                payload.user_id,
                self.bot.events[payload.message_id]["amount"],
            )


async def setup(bot):
    await bot.add_cog(Flowers(bot))
