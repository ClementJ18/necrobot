from itertools import groupby
import random
import discord
from discord.ext import commands
from rings.db import DatabaseError

from rings.utils.checks import has_perms
from rings.utils.ui import Confirm, paginate
from rings.utils.utils import check_channel, BotError, time_string_parser 
from rings.utils.converters import FlowerConverter, GachaBannerConverter, GachaCharacterConverter, TimeConverter

from typing import Union


class Flowers(commands.Cog):
    """A server specific economy system. Use it to reward/punish users at you heart's content."""

    def __init__(self, bot):
        self.bot = bot

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

    #######################################################################
    ## Commands
    #######################################################################

    @commands.group(invoke_without_command=True)
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

        if user is None:
            user = ctx.author

        flowers = await self.get_flowers(ctx.guild.id, user.id)
        symbol = await self.get_symbol(ctx.guild.id)

        await ctx.send(f":atm: | {user.name} has **{flowers}** {symbol}")

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
        characters = await self.bot.db.query("""
            SELECT id, name, title, tier, universe, description, image_url, obtainable, count(rolled.char_id) as total 
            FROM necrobot.Characters as chars
            LEFT JOIN necrobot.RolledCharacters as rolled on chars.id = rolled.char_id
            GROUP BY chars.id
            ORDER BY universe ASC, name ASC
        """)

        if for_banner:
            characters = [character for character in characters if character["obtainable"]]

        def embed_maker(view, entry):
            mutable_entry = dict(entry)
            mutable_entry["name"] = f"{entry['name']} ({view.page_number}/{view.page_count})"
            return self.embed_character(mutable_entry, True)

        await paginate(ctx, characters, 1, embed_maker)

    @characters.command(name="create")
    @has_perms(6)
    async def characters_create(self, ctx, name: str, title: str, universe: str, tier: int):
        """Add a new character 
        
        {usage}
        
        __Examples__
        `{pre}characters create "John" "The Destroyer", "Rift", "2"` - Start the creation process.
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

        await ctx.send("Post a url for the image of the character. Type exit to cancel.")
        start_m = await self.bot.wait_for("message", check=general_check, timeout=300)
        image = start_m.content.strip()
        await msg.edit(embed=embed_maker())

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
                SELECT b.*, array_agg(c.name) as characters FROM necrobot.Banners AS b 
                    JOIN necrobot.BannerCharacters AS bc ON b.id=bc.banner_id 
                    JOIN necrobot.Characters as c ON bc.char_id=c.id
                WHERE guild_id=$1
                group by b.id
            """, ctx.guild.id)
        else:
            banners = await self.bot.db.query("""
                SELECT b.*, array_agg(c.name) as characters FROM necrobot.Banners AS b 
                    JOIN necrobot.BannerCharacters AS bc ON b.id=bc.banner_id 
                    JOIN necrobot.Characters as c ON bc.char_id=c.id
                WHERE guild_id=$1 AND ongoing=true
                group by b.id
            """, ctx.guild.id)


        def embed_maker(view, entry):
            embed = discord.Embed(
                title=f"{entry['name']} ({view.page_number}/{view.page_count})",
                colour=self.bot.bot_color,
                description=entry['description'],
            )

            if entry["image_url"]:
                embed.set_image(url=entry["image_url"])
            embed.set_footer(**self.bot.bot_footer)
            
            embed.add_field(name="Ongoing", value=entry["ongoing"])
            embed.add_field(name="Characters", value=", ".join(entry["characters"]))

            return embed

        await paginate(ctx, banners, 1, embed_maker)

    @banners.command(name="create")
    @has_perms(4)
    async def banners_create(self, ctx, *, name):
        """Add a new banner in the guild. 
        
        {usage}
        
        __Examples__
        `{pre}banner create Rose Lily Banner` - Start the creation for a banner that will last 2 days adn 3h
        """
        description = None
        image = None
        characters = []
        banner_id = None

        def general_check(m):
            if not m.author == ctx.author or not m.channel == ctx.channel:
                return False

            if m.content.lower() == "exit":
                raise BotError("Exited setup")

            return True

        def embed_maker():
            embed = discord.Embed(
                title=name,
                colour=self.bot.bot_color,
                description=description,
            )

            if image is not None:
                embed.set_image(url=image)

            embed.set_footer(**self.bot.bot_footer)
            embed.add_field(name="Characters", value=", ".join([character["name"] for character in characters]))
            embed.add_field(name="ID", value=banner_id)

            return embed

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
            "INSERT INTO necrobot.Banners(guild_id, name, description, image_url) VALUES($1, $2, $3, $4) RETURNING id",
            ctx.guild.id, name, description, image, fetchval=True
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


    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def gacha(self, ctx):
        """Get information on the gacha on this server
        
        {usage}
        
        __Examples__
        `{pre}gacha` - get information on the gacha in this server
        """
        guild = await self.bot.db.query("SELECT roll_cost, symbol FROM necrobot.FlowersGuild WHERE guild_id = $1", ctx.guild.id)
        await ctx.send(f":game_die: | A roll on this server costs {guild[0]['roll_cost']} {guild[0]['symbol']}.")

    def convert_exp_to_level(self, exp):
        level = -1
        thresholds = [
            1,
            3,
            5,
            7,
            10,
        ]

        for threshold in thresholds:
            if exp >= threshold:
                level += 1
                exp -= threshold
            else:
                break

        return level, exp, threshold

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
            WHERE rc.guild_id = $1 AND rc.user_id = $2""", 
            ctx.guild.id, ctx.author.id
        )

        def embed_maker(view, entry):
            mutable_entry = dict(entry)
            mutable_entry["name"] = f"{entry['name']} ({view.page_number}/{view.page_count})"
            return self.embed_character(entry)

        await paginate(ctx, characters, 1, embed_maker)

    def calculate_weight(self, tier, modifier):
        return ( 2 * ( 1 + ( 5 - tier ) ) / 5 ** 2 ) * modifier
    
    def embed_character(self, character, admin=False):
        embed = discord.Embed(
            title=character["name"],
            colour=self.bot.bot_color,
            description=character['description'],
        )

        if character.get("image_url"):
            embed.set_image(url=character["image_url"])

        embed.set_footer(**self.bot.bot_footer)
        embed.add_field(name="ID", value=character["id"])
        embed.add_field(name="Title", value=character["title"])
        embed.add_field(name="Tier", value=f"{character['tier']*':star:'}")
        embed.add_field(name="Origin", value=character["universe"])
    
        if character.get("level"):
            level, exp, next_threshold = self.convert_exp_to_level(character["level"])
            embed.add_field(name="Level", value=f"{level} ({exp}/{next_threshold})")

        if admin and character.get("obtainable"):
            embed.add_field(name="Obtainable", value=character["obtainable"])

        if character.get("total"):
            embed.add_field(name="Count", value=character["total"])

        return embed
    
    async def pay_for_roll(self, guild_id, user_id):
        await self.bot.db.query("""
            UPDATE necrobot.Flowers 
            SET flowers = flowers - (
                SELECT roll_cost FROM necrobot.FlowersGuild WHERE guild_id = $1
            ) WHERE user_id = $2 AND guild_id = $1""", 
            guild_id, user_id
        )

    @gacha.group(name="roll", invoke_without_command=True)
    @commands.guild_only()
    async def gacha_roll(self, ctx, *, banner : GachaBannerConverter):
        try:
            await self.pay_for_roll(ctx.guild.id, ctx.author.id)
        except DatabaseError as e:
            raise BotError("You no longer have enough flowers for a pull.") from e

        characters = await self.bot.db.query("""
            SELECT c.*, bc.modifier FROM necrobot.BannerCharacters as bc 
                JOIN necrobot.Characters as c ON bc.char_id = c.id
            WHERE bc.banner_id = $1""",
            banner["id"]
        )

        weights = [self.calculate_weight(char["tier"], char["modifier"]) for char in characters]
        pulled_char = dict(random.choices(characters, weights=weights, k=1)[0])

        
        level = await self.add_characters_to_user(ctx.guild.id, ctx.author.id, pulled_char["id"])
        pulled_char["level"] = level

        await ctx.send(embed=self.embed_character(pulled_char))

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
