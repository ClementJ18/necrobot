import ast
import time
from datetime import timedelta

import discord
from discord.ext import commands

from rings.utils.checks import has_perms
from rings.utils.ui import Confirm, paginate
from rings.utils.utils import BotError
from rings.utils.var import tutorial_e

from .var import gdpr_e


class Support(commands.Cog):
    """All the NecroBot support commands are here to help you enjoy your time with NecroBot"""

    def __init__(self, bot):
        self.bot = bot
        self.bot.tutorial_e = discord.Embed.from_dict(tutorial_e)
        self.bot.gdpr_embed = discord.Embed.from_dict(gdpr_e)

    #######################################################################
    ## Commands
    #######################################################################

    @commands.command(aliases=["support"])
    async def about(self, ctx: commands.Context):
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
            str(timedelta(seconds=time.time() - self.bot.uptime_start))
            .partition(".")[0]
            .replace(":", "{}")
        )
        embed.add_field(name="Uptime", value=uptime.format("hours, ", "minutes and ") + "seconds")
        embed.add_field(
            name="Links",
            value=f"[Invite bot to your server]({discord.utils.oauth_url(self.bot.user.id, permissions=discord.Permissions(permissions=403172599))}) - [Get help with the bot](https://discord.gg/fPJANsE)",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def report(self, ctx: commands.Context, *, message):
        """Report a bug with the bot or send a suggestion . Please be a specific as you can. Any abusive use will result in
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
            confirm_msg=":white_check_mark: | Report sent!",
        )

        view.message = await ctx.send(
            "You are about to send this bug/suggestion report, are you sure? Abusing the report command can result in blacklisting",
            embed=embed,
            view=view,
        )

        await view.wait()
        if view.value:
            await self.bot.get_channel(398894681901236236).send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def news(self, ctx: commands.Context):
        """See the latest necrobot news

        {usage}

        __Examples__
        `{pre}news` - get the news starting from the latest
        """
        news = self.bot.settings["news"]

        if not news:
            raise BotError("No news available")

        def embed_maker(view, entries):
            return discord.Embed.from_data(news[view.page_number])

        await paginate(ctx, len(news) - 1, embed_maker)

    @news.command("add")
    @has_perms(6)
    async def news_add(self, ctx: commands.Context, *, news: str):
        """Add a new news item

        {usage}"""
        try:
            news = ast.literal_eval(news)
        except ValueError as e:
            await ctx.send(str(e))
            return

        base_d = {
            "author": {
                "name": "Necrobot's Anchorman",
                "url": "https://discord.gg/Ape8bZt",
                "icon_url": self.bot.user.display_avatar.replace(format="png", size=128),
            },
            "color": 161712,
            "type": "rich",
        }
        news_e = {**news, **base_d}
        embed = discord.Embed.from_data(news_e)
        view = Confirm()
        view.message = await ctx.send(embed=embed, view=view)
        await view.wait()

        if view.value:
            self.bot.settings["news"] = [news, *self.bot.settings["news"]]
            await ctx.send(f":white_check_mark: | Added **{news['title']}** news")
            channel = self.bot.get_channel(436595183010709514)
            await channel.send(embed=embed)

    @news.command("delete")
    @has_perms(6)
    async def news_delete(self, ctx: commands.Context, index: int):
        """Remove a news item

        {usage}"""
        if not self.bot.settings["news"]:
            raise BotError("No news available")

        if not 0 <= index < len(self.bot.settings["news"]):
            raise BotError(
                f"Not a valid index, pick a number between 1 and {len(self.bot.settings['news'])}"
            )

        news = self.bot.settings["news"].pop(index)
        await ctx.send(f":white_check_mark: | News **{news['title']}** removed")

    @news.command("raw")
    @has_perms(6)
    async def news_raw(self, ctx: commands.Context, index: int):
        """Get the raw dict form of the news

        {usage}"""
        await ctx.send(self.bot.settings["news"][index])

    @news.command("template")
    @has_perms(6)
    async def news_template(self, ctx: commands.Context):
        """Prints the template for news

        {usage}"""
        await ctx.send(
            '{ "fields": [{"inline": False, "name": "Why is good 1", "value": "Because"}], "description": "", "title": ""}'
        )

    @commands.command()
    async def tutorial(self, ctx: commands.Context):
        """Sends an embed with helpful information on Necrobot's features, be warned, it is quite a dense text blob

        {usage}"""
        try:
            await ctx.author.send(embed=self.bot.tutorial_e)
        except discord.errors.Forbidden as e:
            raise BotError("Looks like you have private messages disabled") from e

    @commands.command()
    async def privacy(self, ctx: commands.Context):
        """Get information on the data necrobot keeps about you and what steps you can do about it.

        {usage}"""
        try:
            await ctx.author.send(embed=self.bot.gdpr_embed)
        except discord.Forbidden as e:
            raise BotError("Looks like you have private messages disabled") from e
