#!/usr/bin/python3.6
import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from bs4 import BeautifulSoup
import aiohttp

class Modding():
    """The modding commands that allow modders to showcase their work and users to interact with it. This is NecroBot's main purpose albeit one of his smallest feature now."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    @commands.cooldown(1, 5, BucketType.channel)
    async def moddb(self, cont, url):
        """This command takes in a mod url from ModDB and returns a rich embed of it. Due to the high variety of mod formats, embed appearances will vary but it should always return one as long as it is given a proper url starting with `http://www.moddb.com/mods/`
        \n
        {}
        \n
        __Example__
        `n!moddb http://www.moddb.com/mods/edain-mod` - creates a rich embed of the Edain Mod ModDB page"""
        if cont.args[0].startswith("http://www.moddb.com/mods/"):
            #obtain xml and html pages
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    soup = BeautifulSoup(await resp.text(), "html.parser")

                async with session.get(url.replace("www","rss") + "/articles/feed/rss.xml") as resp:
                    rss = BeautifulSoup(await resp.text(), "xml")

            modName = str(soup.title.string[:-9])

            try:
                modDesc = str(soup.find(itemprop="description")["content"])
            except KeyError:
                modDesc = str(soup.find(itemprop="description").string)

            embed = discord.Embed(title="__**{0}**__".format(modName), colour=discord.Colour(0x277b0), url=url, description=modDesc)
            embed.set_author(name="ModDB", url="http://www.moddb.com", icon_url="http://i.imgur.com/aExydLm.png")
            embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")
            
            #navbar
            sections = ["Articles","Reviews","Downloads","Videos","Images"]
            navBar = ["[{0}]({1}/{0})".format(x, url) for x in sections]
            embed.add_field(name="Navigation", value=" - ".join(navBar))

            #recent articles
            articles = rss.find_all("item")[:3]
            for article in articles:
                title = str(article.title.string)
                desc = str(article.find_all(type="plain")[1].string)
                link = str(article.link.string)
                date = str(article.pubDate.string[:-14])
                embed.add_field(name=title, value="{0}... [Link]({1})\nPublished {2}".format(desc, link, date))

            #tags
            tags = soup.find(id="tagsform")
            tagList = list()
            for x in tags.descendants:
                if str(type(x)) == "<class 'bs4.element.NavigableString'>":
                    if len(x) > 0 and x != "\n" and x != " ":
                        tagList.append(str(x))

            embed.add_field(name="\u200b", value="#" + " #".join(tagList[:-1]))

            #misc stuff
            misc = soup.find_all("h5")
            try:
                follow = ["[Follow the mod](" + x.parent.a["href"] + ")" for x in misc if x.string == "Mod watch"][0]
            except IndexError:
                follow = "Cannot follow"
            try: 
                publishers = "Creator: " + [x.parent.a.string for x in misc if x.string in ["Developer", "Creator"]][0]
            except IndexError:
                follow = "No Creator"

            #comment
            comment = "[Leave a comment]({0}#commentform)".format(url)

            #release date
            release_date = "Release: {0}".format(soup.time.string)

            #rating
            try:
                score = str("Average Rating: " + soup.find(itemprop="ratingValue")["content"])
            except TypeError:
                score = "Average Rating: Not rated"
            
            embed.add_field(name="Misc: ", value="{0} \n{1}  -  {2}\n**{3}**  -  **{4}**".format(score, publishers, release_date, comment, follow))

            #style
            finrodList = list()
            styleList = ["Genre","Theme","Players"]
            for y in styleList:
                try:
                    style = "**" + y + "**: " + [x.parent.a.string for x in misc if x.string == y][0]
                except IndexError:
                    style = "**" + y +"**: None"
                finrodList.append(style)

            embed.add_field(name="Style", value= "\n".join(finrodList), inline=True)

            #stats
            finrodList = list()
            statsList = [["Rank","Unclassed"],["Visits","Not Tracked"],["Files","0"],["Articles","0"],["Reviews","0"]]
            for y in statsList:
                try:
                    stat = "__" + y[0] + "__: " + [x.parent.a.string for x in misc if x.string == y[0]][0]
                except IndexError:
                    stat = "__" + y[0] + "__: " + y[1]
                finrodList.append(stat)

            try:
                finrodList.append("__Last Update__: " + [x.parent.time.string for x in misc if x.string == "Last Update"][0])
            except IndexError:
                finrodList.append("__Last Update__: None")

            embed.add_field(name="Stats", value= "\n".join(finrodList))

            #you may also like
            suggestionList = list()
            suggestions = soup.find(string="You may also like").parent.parent.parent.parent.find_all(class_="row clear")
            for x in suggestions:
                link = x.find("a",class_="heading")
                suggestionList.append("[{0}]({1})".format(link.string, link["href"]))

            embed.add_field(name="You may also like",value=" - ".join(suggestionList))
            await self.bot.say(embed=embed)
            await self.bot.delete_message(cont.message)

        else:
            await self.bot.say("URL was not valid, try again with a valid url. URL must be from an existing mod page. Accepted examples: `http://www.moddb.com/mods/edain-mod`, `http://www.moddb.com/mods/rotwk-hd-edition`, ect...")

def setup(bot):
    bot.add_cog(Modding(bot))