import discord
from discord.ext import commands

from rings.utils.utils import react_menu, BotError
from rings.utils.var import tutorial_e, gdpr_e
from rings.utils.checks import has_perms

import ast
import time
from datetime import timedelta


class Support(commands.Cog):
    """All the NecroBot support commands are here to help you enjoy your time with NecroBot """
    def __init__(self, bot):
        self.bot = bot
        self.bot.tutorial_e = discord.Embed.from_dict(tutorial_e)
        self.bot.gdpr_embed = discord.Embed.from_dict(gdpr_e)
        
    #######################################################################
    ## Commands
    #######################################################################
    
    @commands.command(aliases=["support"])
    async def about(self, ctx):
        """Creates a rich embed of the bot's details Also contains link for inviting and support server.

        {usage}"""

        bot_desc = "Hello! :wave: I'm NecroBot, a moderation bot with many commands for a wide variety of server and a high modularity which means you can enable/disable just about every part of me as you wish."
        embed = discord.Embed(title="NecroBot", colour=self.bot.bot_color, description=bot_desc)
        embed.set_footer(**self.bot.bot_footer)
        embed.add_field(name="About", value=f"I'm currently in {len(list(self.bot.guilds))} guilds and I can see {len(list(self.bot.users))} members. I was created using Python and the d.py library. ", inline=False)
        embed.add_field(name="Version", value=self.bot.version)
        uptime = str(timedelta(seconds=time.time() - self.bot.uptime_start)).partition(".")[0].replace(":", "{}")
        embed.add_field(name="Uptime", value=uptime.format("hours, ", "minutes and ") + "seconds")
        embed.add_field(name="Links", value=f"[Invite bot to your server]({discord.utils.oauth_url(self.bot.user.id, discord.Permissions(permissions=403172599))}) - [Get help with the bot](https://discord.gg/fPJANsE)", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def report(self, ctx, *, message):
        """Report a bug with the bot or send a suggestion . Please be a specific as you can. Any abusive use will result in
        blacklisting.

        {usage}

        __Examples__
        `{pre}report profile while using profile the picture came out wrong, it was all distorted and stuff and my data on it was wrong.` - report 
        a bug for `profile`
        `{pre}report settings while using the sub-command mute it told me there was no such role when there is indeed` - report a bug for 
        `settings`"""

        embed = discord.Embed(title=":bulb: A report has just came in :bulb:", description=message, colour=self.bot.bot_color)
        embed.set_footer(**self.bot.bot_footer)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Helpful Info", value=f"User: {ctx.author.mention} \nServer: {ctx.guild.name} \nServer ID: {ctx.guild.id}")
        
        msg = await ctx.send("You are about to send this report, are you sure? Abusing the report command can result in blacklisting", embed=embed)
        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["\N{WHITE HEAVY CHECK MARK}", "\N{NEGATIVE SQUARED CROSS MARK}"] and msg.id == reaction.message.id

        reaction, _ = await self.bot.wait_for(
            "reaction_add", 
            check=check, 
            timeout=300, 
            handler=msg.clear_reactions, 
            propagate=False
        )

        if reaction.emoji == "\N{NEGATIVE SQUARED CROSS MARK}":
            await msg.clear_reactions()
        elif reaction.emoji == "\N{WHITE HEAVY CHECK MARK}":
            await ctx.send(":white_check_mark: | Report sent!")
            await msg.clear_reactions()
            await self.bot.get_channel(398894681901236236).send(embed=embed)
        

    @commands.group(invoke_without_command=True)
    async def news(self, ctx, index : int = 1):
        """See the latest necrobot news

        {usage}

        __Examples__
        `{pre}news` - get the news starting from the latest
        `{pre}news 4` - get the news starting from the fourth item
        `{pre}news 1` - get the news starting from the first item"""
        news = self.bot.settings["news"]

        if not news:
            await ctx.send(":negative_squared_cross_mark: | No news available")
            return

        if 0 >= index > len(news):
            await ctx.send(f":negative_squared_cross_mark: | Not a valid index, pick a number from 1 to {len(news)}")
            return
        
        def _embed_generator(page):
            return discord.Embed.from_data(news[page])

        await react_menu(ctx, len(news) - 1, _embed_generator, index-1)

    @news.command("add")
    @has_perms(6)
    async def news_add(self, ctx, *, news : str):
        """Add a new news item

        {usage}"""
        try:
            news = ast.literal_eval(news)
        except ValueError as e:
            await ctx.send(str(e))
            return

        base_d = {
            "author": {
                "name": "Necrobot's Anchorman", "url": "https://discord.gg/Ape8bZt", 
                "icon_url": self.bot.user.avatar_url_as(format="png", size=128)
            }, 
            "color": 161712, "type": "rich"
        }
        news_e = {**news , **base_d}
        embed = discord.Embed.from_data(news_e)
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        def check(reaction, user):
            return user == ctx.author and reaction.emoji in ["\N{NEGATIVE SQUARED CROSS MARK}", "\N{WHITE HEAVY CHECK MARK}"] and msg.id == reaction.message.id

        reaction, _ = await self.bot.wait_for(
            "reaction_add", 
            check=check, 
            handler=msg.clear_reactions, 
            propagate=False
        )

        if reaction.emoji == "\N{WHITE HEAVY CHECK MARK}":
            self.bot.settings["news"] = [news, *self.bot.settings["news"]]
            await ctx.send(f":white_check_mark: | Added **{news['title']}** news")
            channel = self.bot.get_channel(436595183010709514)
            await channel.send(embed=embed)

        await msg.clear_reactions()


    @news.command("delete")
    @has_perms(6)
    async def news_delete(self, ctx, index : int):
        """Remove a news item

        {usage}"""
        if not self.bot.settings["news"]:
            await ctx.send(":negative_squared_cross_mark: | No news available")
            return

        if not 0 <= index < len(self.bot.settings["news"]):
            await ctx.send(f":negative_squared_cross_mark: | Not a valid index, pick a number between 1 and {len(self.bot.settings['news'])}")
            return

        news = self.bot.settings["news"].pop(index)
        await ctx.send(f":white_check_mark: | News **{news['title']}** removed")

    @news.command("raw")
    @has_perms(6)
    async def news_raw(self, ctx, index : int):
        """Get the raw dict form of the news

        {usage}"""
        await ctx.send(self.bot.settings["news"][index])

    @news.command("template")
    @has_perms(6)
    async def news_template(self, ctx):
        """Prints the template for news

        {usage}"""
        await ctx.send('{ "fields": [{"inline": False, "name": "Why is good 1", "value": "Because"}], "description": "", "title": ""}')

    @commands.command()
    async def tutorial(self, ctx):
        """Sends an embed with helpful information on Necrobot's features, be warned, it is quite a dense text blob

        {usage}"""
        try:
            await ctx.author.send(embed=self.bot.tutorial_e)
        except discord.errors.Forbidden:
            raise BotError("Looks like you have private messages disabled")

    @commands.command()
    async def privacy(self, ctx):
        """Get information on the data necrobot keeps about you and what steps you can do about it.

        {usage}"""
        try:
            await ctx.send(embed=self.bot.gdpr_embed)
        except discord.Forbidden:
            raise BotError("Looks like you have private messages disabled")

        
def setup(bot):
    bot.add_cog(Support(bot))
