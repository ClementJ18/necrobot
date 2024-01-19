from __future__ import annotations

import time
from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from rings.utils.ui import Confirm
from rings.utils.utils import POSITIVE_CHECK, BotError
from rings.utils.var import tutorial_e

from .var import gdpr_e

if TYPE_CHECKING:
    from bot import NecroBot


class Support(commands.Cog):
    """All the support commands are here to help you enjoy your time with NecroBot"""

    def __init__(self, bot: NecroBot):
        self.bot = bot
        self.bot.tutorial_e = discord.Embed.from_dict(tutorial_e)
        self.bot.gdpr_embed = discord.Embed.from_dict(gdpr_e)

    #######################################################################
    ## Commands
    #######################################################################

    @commands.command(aliases=["support"])
    async def about(self, ctx: commands.Context[NecroBot]):
        """Creates a rich embed of the bot's details Also contains link for inviting and support server.

        {usage}"""

        bot_desc = "Hello! :wave: I'm NecroBot, a moderation bot with many commands for a wide variety of server and a high modularity which means you can enable/disable just about every part of me as you wish."
        embed = discord.Embed(title="NecroBot", colour=self.bot.bot_color, description=bot_desc)
        embed.set_footer(**self.bot.bot_footer)
        embed.add_field(
            name="About",
            value=f"I'm currently in {len(list(self.bot.guilds))} guilds and I can see {len(list(self.bot.users))} members. I was created using Python and the d.py library. ",
            inline=False,
        )
        embed.add_field(name="Version", value=self.bot.version)
        uptime = (
            str(timedelta(seconds=time.time() - self.bot.uptime_start)).partition(".")[0].replace(":", "{}")
        )
        embed.add_field(name="Uptime", value=uptime.format("hours, ", "minutes and ") + "seconds")
        embed.add_field(
            name="Links",
            value=f"[Invite bot to your server]({discord.utils.oauth_url(self.bot.user.id, permissions=discord.Permissions(permissions=403172599))}) - [Get help with the bot](https://discord.gg/fPJANsE)",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def report(self, ctx: commands.Context[NecroBot], *, message):
        """Report a bug with the bot or send a suggestion . Please be a specific as you can. Any abusive use will result in \
        blacklisting.

        {usage}

        __Examples__
        `{pre}report profile while using profile the picture came out wrong, it was all distorted and stuff and my data on it was wrong.` - report
        a bug for `profile`
        `{pre}report settings while using the sub-command mute it told me there was no such role when there is indeed` - report a bug for
        `settings`"""

        embed = discord.Embed(
            title=":bulb: A report has just came in :bulb:",
            description=message,
            colour=self.bot.bot_color,
        )
        embed.set_footer(**self.bot.bot_footer)
        embed.set_author(
            name=str(ctx.author),
            icon_url=ctx.author.display_avatar.replace(format="png", size=128),
        )
        embed.add_field(
            name="Helpful Info",
            value=f"User: {ctx.author.mention} \nServer: {ctx.guild.name} \nServer ID: {ctx.guild.id}",
        )

        view = Confirm(
            ctx.author,
            confirm_msg=f"{POSITIVE_CHECK} | Report sent!",
        )

        view.message = await ctx.send(
            "You are about to send this bug/suggestion report, are you sure? Abusing the report command can result in blacklisting",
            embed=embed,
            view=view,
        )

        await view.wait()
        if view.value:
            await self.bot.get_channel(398894681901236236).send(embed=embed)

    @commands.command()
    async def tutorial(self, ctx: commands.Context[NecroBot]):
        """Sends an embed with helpful information on Necrobot's features, be warned, it is quite a dense text blob

        {usage}"""
        try:
            await ctx.author.send(embed=self.bot.tutorial_e)
        except discord.errors.Forbidden as e:
            raise BotError("Looks like you have private messages disabled") from e

    @commands.command()
    async def privacy(self, ctx: commands.Context[NecroBot]):
        """Get information on the data necrobot keeps about you and what steps you can do about it.

        {usage}"""
        try:
            await ctx.author.send(embed=self.bot.gdpr_embed)
        except discord.Forbidden as e:
            raise BotError("Looks like you have private messages disabled") from e
