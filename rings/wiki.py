import discord
from discord.ext import commands

import rings.utils.wikia as wikia
from rings.utils.utils import BotError

import re
import urllib
from unwiki.unwiki import UnWiki
from fuzzywuzzy import process

class Wiki(commands.Cog):
    """A series of wikia-related commands. Used to search the biggest fan-made database of 
    information."""
    def __init__(self, bot):
        self.bot = bot
        
    async def wikia_handler(self, ctx, wiki, article):
        base = f"https://{wiki}.wikia.com"
        if article is None:
            return await ctx.send(f"<{base}>")

        
        results = await wikia.search(self, wiki, article)
        
        if not results:
            raise BotError("Could not find any article matching the query on that wiki")
            
        
        page = await wikia.page(self, wiki, results[0]["id"])
        
        msg = "List of results: {}".format(", ".join([x["title"] for x in results[1:]]))

        url = base + page["url"]
        embed = discord.Embed(
            title=page["title"], 
            colour=discord.Colour(0x277b0), 
            url=url, 
            description=page["abstract"])

        if page["thumbnail"]:
            embed.set_thumbnail(url=page["thumbnail"])

        if wiki == "edain":
            icon = "https://i.imgur.com/lPPQzRg.png"
        else:
            icon = "https://vignette.wikia.nocookie.net/aotr/images/6/64/Favicon.ico"

        embed.set_author(name=f"{wiki.title()} Wiki", url=base, icon_url=icon)
        embed.set_footer(text="Generated by NecroBot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
        
        related_pages = await wikia.related(self, wiki, results[0]["id"])
        related_string = ""
        for related in related_pages:
            link = related["url"].replace(')', '\)')
            related_string += f"- [{related['title']}]({base}{link})\n"

        embed.add_field(name="More Pages", value=related_string, inline=False)
            
        await ctx.send(msg, embed=embed)
    
    @commands.command()
    async def edain(self, ctx, *, article : str = None):
        """Performs a search on the Edain Mod Wiki for the give article name. If an article is found then it will 
        return a rich embed of it, else it will return a list of a related articles and an embed of the first related article. 
        
        {usage}
        
        __Example__
        `{pre}edain Castellans` - print a rich embed of the Castellans page
        `{pre}edain Battering Ram` - prints a rich embed of the Battering Ram disambiguation page"""
        async with ctx.typing():
            await self.wikia_handler(ctx, "edain", article)

    @commands.command()
    async def aotr(self, ctx, *, article : str = None):
        """Performs a search on the Age of the Ring Wiki for the give article name. If an article is found then it will 
        return a rich embed of it, else it will return a list of a related articles and an embed of the first related article. 
        
        {usage}
        
        __Example__
        `{pre}edain Castellans` - print a rich embed of the Castellans page
        `{pre}edain Battering Ram` - prints a rich embed of the Battering Ram disambiguation page"""
        async with ctx.typing():
            await self.wikia_handler(ctx, "aotr", article)
        
    @commands.command()
    async def wiki(self, ctx, sub_wiki, *, article : str = None):
        """Performs a search on the given wiki (if valid) for the given article name. If an article is found then it 
        will return a rich embed of it, else it will return a list of a related articles and an embed of the first related article. 

        {usage}

        __Example__
        `{pre}wiki disney Donald Duck` - creates a rich embed of the Donald Duck page
        `{pre}wiki transformers Optimus` - searches for the 'Optimus Page' and returns a list of search results and a
        rich embed of the first one."""
        async with ctx.typing(): 
            await self.wikia_handler(ctx, sub_wiki, article)        

def setup(bot):
    bot.add_cog(Wiki(bot))
