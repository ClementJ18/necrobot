import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

import wikia

class Wiki():
    def __init__(self, bot):
        self.bot = bot

    #create a rich embed for an article or searches for articles on the Edain Mod Wiki
    @commands.command()
    @commands.cooldown(2, 5, BucketType.user)
    async def edain(self,*,arg0 : str):
        try:
            article = wikia.page("Edain", arg0)
            url = article.url.replace(" ","_")
            related ="  - " + "\n   - ".join(article.related_pages[:3])

            embed = discord.Embed(title="__**" + article.title + "**__", colour=discord.Colour(0x277b0), url=url, description=article.section(article.sections[0]))

            embed.set_thumbnail(url=article.images[0]+"?size=400")
            embed.set_author(name=article.sub_wikia + " Wiki", url="http://edain.wikia.com/", icon_url="http://i.imgur.com/lPPQzRg.png")
            embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

            if len(article.section("Abilities")) < 2048 :
                embed.add_field(name="Abilities", value=article.section("Abilities"))
            else:
                for x in article.sections[1:]:
                    if len(x) < 2048:
                        embed.add_field(name=x, value=article.section(x))
                        break

            embed.add_field(name="More Pages:", value=related)
            embed.add_field(name="Quotes", value="Get all the sound quotes for units/heroes [here](http://edain.wikia.com/wiki/Edain_Mod_Soundsets)")

            await self.bot.say(embed=embed)
        except wikia.wikia.WikiaError:
            try:
                article = wikia.search("Edain", arg0)
                await self.bot.say("Article: **"+ arg0 +"** not found, performing search instead, please search again using one of the possible relevant articles below:\n - " + "\n - ".join(article))
            except ValueError:
                await self.bot.say("Article not found, and search didn't return any results. Please try again with different terms.")

    #create a rich embed for an article or searches for articles on the LOTR Wiki
    @commands.command()
    @commands.cooldown(2, 5, BucketType.user)
    async def lotr(self,*,arg0 : str):
        try:
            article = wikia.page("lotr", arg0)
            url = article.url.replace(" ","_")
            related ="  - " + "\n  - ".join(article.related_pages[:3])

            embed = discord.Embed(title="__**" + article.title + "**__", colour=discord.Colour(0x277b0), url=url, description=article.section(article.sections[0]))

            embed.set_thumbnail(url=article.images[0]+"?size=400")
            embed.set_author(name="LOTR Wiki", url="http://lotr.wikia.com/", icon_url="http://i.imgur.com/YWn19eW.png")
            embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

            embed.add_field(name="More Pages:", value=related)

            await self.bot.say(embed=embed)
        except wikia.wikia.WikiaError:
            try:
                article = wikia.search("lotr", arg0)
                await self.bot.say("Article not found, performing search instead, please search again using one of the possible relevant articles below:\n - " + "\n - ".join(article))
            except ValueError:
                await self.bot.say("Article not found, and search didn't return any result. Please try again with different terms.")

    #create a rich embed for an article or searches for articles on a given wiki
    @commands.command()
    @commands.cooldown(2, 5, BucketType.user)
    async def wiki(self, arg0,*,arg1):
        try:
            article = wikia.page(arg0, arg1)
            url = article.url.replace(" ","_")
            related ="  - " + "\n  - ".join(article.related_pages[:5])

            embed = discord.Embed(title="__**" + article.title + "**__", colour=discord.Colour(0x277b0), url=url, description=article.section(article.sections[0]))

            embed.set_thumbnail(url=article.images[0]+"?size=400")
            embed.set_author(name=article.sub_wikia.title() + " Wiki", url="http://"+ article.sub_wikia + ".wikia.com/", icon_url="https://vignette3.wikia.nocookie.net/"+ article.sub_wikia +"/images/6/64/Favicon.ico")
            embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

            embed.add_field(name="More Pages:", value=related)

            await self.bot.say(embed=embed)
        except wikia.wikia.WikiaError:
            try:
                article = wikia.search(arg0, arg1)
                await self.bot.say("Article not found, performing search instead, please search again using one of the possible relevant articles below:\n - " + "\n - ".join(article))
            except ValueError:
                await self.bot.say("Article not found or wiki not recognized, and search didn't return any result. Please try again with different terms.")

def setup(bot):
    bot.add_cog(Wiki(bot))