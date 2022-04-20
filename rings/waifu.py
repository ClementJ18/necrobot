import discord
from discord.ext import commands

from rings.utils.checks import has_perms
from rings.utils.utils import check_channel, BotError
from rings.utils.converters import FlowerConverter, TimeConverter

from typing import Union

class Flowers(commands.Cog):
    """A server specific economy system. Use it to reward/punish users at you heart's content."""
    def __init__(self, bot):
        self.bot = bot

    #######################################################################
    ## Cog Functions
    #######################################################################

    def cog_check(self, ctx):
        if ctx.guild:
            return True

        raise commands.CheckFailure("This command cannot be used in private messages.")

    #######################################################################
    ## Functions
    ####################################################################### 

    async def add_flowers(self, guild_id, user_id, amount):
        await self.bot.db.query(
            "UPDATE necrobot.Flowers SET flowers = flowers + $3 WHERE guild_id=$1 AND user_id=$2",
            guild_id, user_id, amount
        )

    async def transfer_flowers(self, guild_id, payer, payee, amount):
        await self.add_flowers(guild_id, payer, -amount)
        await self.add_flowers(guild_id, payee, amount)

    async def get_flowers(self, guild_id, user_id):
        flowers = await self.bot.db.query(
            "SELECT flowers FROM necrobot.Flowers WHERE guild_id=$1 AND user_id=$2",
            guild_id, user_id
        )

        return flowers[0][0]

    async def get_symbol(self, guild_id):
        symbol = await self.bot.db.query(
            "SELECT symbol FROM necrobot.FlowersGuild WHERE guild_id=$1",
            guild_id
        )

        return symbol[0][0]

    async def update_symbol(self, guild_id, symbol):
        await self.bot.db.query(
            "UPDATE necrobot.FlowersGuild SET symbol=$2 WHERE guild_id=$1",
            guild_id, symbol
        )

    #######################################################################
    ## Commands
    #######################################################################    

    @commands.group(invoke_without_command=True)
    @has_perms(3)
    async def flowers(self, ctx, member : discord.Member, amount : int, *, reason : str = None):
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
        await ctx.send(msg.format(amount=abs(amount), symbol=await self.get_symbol(ctx.guild.id), member=member))

    @flowers.command(name="symbol")
    @has_perms(4)
    async def flowers_symbol(self, ctx, symbol : str):
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
    async def flowers_balance(self, ctx, user: discord.Member = None):
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

        await ctx.send(f":atm: | {user.name} has **{flowers}**{symbol}")

    @commands.command()
    @has_perms(3)
    async def event(self, ctx, channel : Union[discord.Thread, discord.TextChannel], amount : int, time : TimeConverter = 86400):
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

        embed = discord.Embed(color=self.bot.bot_color, title="Flower Event", description=f"React with :cherry_blossom: to gain **{amount}** {symbol}. This event will last {time_format}")
        embed.set_footer(**self.bot.bot_footer)
        msg = await channel.send(embed=embed, delete_after=time)
        await msg.add_reaction("\N{CHERRY BLOSSOM}")
        self.bot.events[msg.id] = {"users":[], "amount":amount}


    @commands.command()
    async def give(self, ctx, member : discord.Member, amount : FlowerConverter):
        """Transfer flowers from one user to another.

        {usage}

        __Examples__
        `{pre}give 100 @ThisGuy` - give 100 flowers to user ThisGuy"""
        await self.transfer_flowers(ctx.guild.id, ctx.author.id, member.id, amount)

        symbol = await self.get_symbol(ctx.guild.id)
        await ctx.send(f":white_check_mark: | **{ctx.author.display_name}** has gifted **{amount}** {symbol} to **{member.display_name}**")

    #######################################################################
    ## Events
    #######################################################################

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id in self.bot.settings["blacklist"]:
            return

        if payload.emoji.name == "\N{CHERRY BLOSSOM}" and payload.message_id in self.bot.events:
            if payload.user_id in self.bot.events[payload.message_id]["users"]:
                return

            self.bot.events[payload.message_id]["users"].append(payload.user_id)
            await self.add_flowers(payload.guild_id, payload.user_id, self.bot.events[payload.message_id]["amount"])

async def setup(bot):
    await bot.add_cog(Flowers(bot))
