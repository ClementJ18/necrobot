#!/usr/bin/python3.6
#!/usr/bin/env python -W ignore::DeprecationWarning

import discord
from discord.ext import commands
from simpleeval import simple_eval
import time
import aiohttp
import random
from overwatch_api.core import AsyncOWAPI
from overwatch_api.constants import *
import re
import json
import asyncio
import urbandictionary as ud
from googletrans import Translator
from PyDictionary import PyDictionary 
from bs4 import BeautifulSoup

class NecroBotPyDict(PyDictionary):
    def __init__(self, *args):
        try:
            if isinstance(args[0], list):
                self.args = args[0]
            else:
                self.args = args
        except:
            self.args = args

    @staticmethod
    async def meaning(term):
        if len(term.split()) > 1:
            print("Error: A Term must be only a single word")
        else:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://wordnetweb.princeton.edu/perl/webwn?s={0}".format(term)) as resp:
                        html = BeautifulSoup(await resp.text(), "html.parser")
                types = html.findAll("h3")
                length = len(types)
                lists = html.findAll("ul")
                out = {}
                for a in types:
                    reg = str(lists[types.index(a)])
                    meanings = []
                    for x in re.findall(r'\((.*?)\)', reg):
                        if 'often followed by' in x:
                            pass
                        elif len(x) > 5 or ' ' in str(x):
                            meanings.append(x)
                    name = a.text
                    out[name] = meanings
                return out
            except Exception as e:
                print("Error: The Following Error occured: %s" % e)

dictionary = NecroBotPyDict() 
translator = Translator()


class Utilities():
    """A bunch of useful commands to do various tasks."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def calc(self, ctx, *, equation : str):
        """Evaluates a pythonics mathematical equation, use the following to build your mathematical equations:
        `*` - for multiplication
        `+` - for additions
        `-` - for substractions
        `/` - for divisons
        `**` - for exponents
        `%` - for modulo
        More symbols can be used, simply research 'python math symbols'
        
        {usage}
        
        __Example__
        `{pre}calc 2 + 2` - 4
        `{pre}calc (4 + 5) * 3 / (2 - 1)` - 27
        """
        try:
            final = simple_eval(equation)
            await ctx.channel.send(":1234: | **" + str(final) + "**")
        except NameError:
            await ctx.channel.send(":negative_squared_cross_mark: | **Mathematical equation not recognized.**")

    @commands.command(aliases=["pong"])
    async def ping(self, ctx):
        """Pings the user and returns the time it took. 
        
        {usage}"""
        pingtime = time.time()
        pingms = await ctx.channel.send(" :clock1: | Pinging... {}'s location".format(ctx.message.author.display_name))
        ping = time.time() - pingtime
        await pingms.edit_message(pingms, ":white_check_mark: | The ping time is `% .01f seconds`" % ping)

    #prints a rich embed of the server info it was called in
    @commands.command()
    async def serverinfo(self, ctx):
        """Returns a rich embed of the server's information. 
        
        {usage}"""
        guild = ctx.message.guild
        embed = discord.Embed(title="__**{}**__".format(guild.name), colour=discord.Colour(0x277b0), description="Info on this server")
        embed.set_thumbnail(url=guild.icon_url.replace("webp","jpg"))
        embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

        embed.add_field(name="**Date Created**", value=guild.created_at.strftime("%d - %B - %Y %H:%M"))
        embed.add_field(name="**Owner**", value=guild.owner.name + "#" + guild.owner.discriminator, inline=True)

        embed.add_field(name="**Default Channel**", value=guild.default_channel)
        embed.add_field(name="**Members**", value=guild.member_count, inline=True)

        embed.add_field(name="**Region**", value=guild.region)
        embed.add_field(name="**Server ID**", value=guild.id, inline=True)

        channelList = [channel.name for channel in guild.channels]
        roleList = [role.name for role in guild.roles]
        embed.add_field(name="**Channels**", value="{}: {}".format(len(channelList), ", ".join(channelList)))
        embed.add_field(name="**Roles**", value="{}: {}".format(len(roleList), ", ".join(roleList)))

        await ctx.channel.send(embed=embed)

    @commands.command()
    async def avatar(self, ctx, user : discord.Member=None):
        """Returns a link to the given user's profile pic 
        
        {usage}
        
        __Example__
        `{pre}avatar @NecroBot` - return the link to NecroBot's avatar"""
        if user is None:
            user = ctx.message.author

        await ctx.channel.send(user.avatar_url.replace("webp","jpg"))

    @commands.group(invoke_without_command = True)
    async def today(self, ctx, date : str =""):
        """Creates a rich information about events/deaths/births that happened today or any day you indicate using the `mm/dd` format

        {usage}

        __Example__
        `{pre}today ` - prints stuff that happened today
        `{pre}today 02/14` - prints stuff that happened on the 14th of February"""

        await ctx.invoke(self.bot.get_command("today {}".format(random.choice(["events", "deaths", "births"]))),date)
        

    @today.command(name="events")
    async def today_events(self, ctx, date : str = ""):
        """Creates a rich information about events that happened today or any day you indicate using the `mm/dd` format

        {usage}

        __Example__
        `{pre}today events` - prints five events that happened today
        `{pre}today events 02/14` - prints five events that happened on the 14th of February"""
        if date != "":
            date = "/"+date


        async with aiohttp.ClientSession() as cs:
            async with cs.get('http://history.muffinlabs.com/date'+date) as r:
                try:
                    res = await r.json(content_type="text/html")
                except:
                     res = await r.json(content_type="application/javascript")

        embed = discord.Embed(title="__**" + res["date"] + "**__", colour=discord.Colour(0x277b0), url=res["url"], description="Necrobot is proud to present: **Events today in History**")
        embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")
        
        for event in random.sample(res["data"]["Events"],5):
            try:
                link_list = "".join(["\n-[{}]({})".format(x["title"], x["link"]) for x in event["links"]])
                embed.add_field(name="Year {}".format(event["year"]), value="{}\n__Links__{}".format(event["text"], link_list), inline=False)
            except AttributeError:
                pass

        await ctx.channel.send(embed=embed)

    @today.command(name="deaths")
    async def today_deaths(self, ctx, date=""):
        """Creates a rich information about deaths that happened today or any day you indicate using the `mm/dd` format

        {usage}

        __Example__
        `{pre}today deaths` - prints deaths that happened today
        `{pre}today deaths 02/14` - prints deaths that happened on the 14th of February"""
        if date != "":
            date = "/"+date


        async with aiohttp.ClientSession() as cs:
            async with cs.get('http://history.muffinlabs.com/date'+date) as r:
                try:
                    res = await r.json(content_type="text/html")
                except:
                     res = await r.json(content_type="application/javascript")

        embed = discord.Embed(title="__**" + res["date"] + "**__", colour=discord.Colour(0x277b0), url=res["url"], description="Necrobot is proud to present: **Deaths today in History**")
        embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

        for death in random.sample(res["data"]["Deaths"], 15):
            try:
                embed.add_field(name="Year {}".format(death["year"]), value="[{}]({})".format(death["text"].replace("b.","Birth: "), death["links"][0]["link"]), inline=False)
            except AttributeError:
                pass

        await ctx.channel.send(embed=embed)


    @today.command(name="births")
    async def today_births(self, ctx, date=""):
        """Creates a rich information about births that happened today or any day you indicate using the `mm/dd` format

        {usage}

        __Example__
        `{pre}today births` - prints births that happened today
        `{pre}today births 02/14` - prints births that happened on the 14th of February"""
        if date != "":
            date = "/"+date


        async with aiohttp.ClientSession() as cs:
            async with cs.get('http://history.muffinlabs.com/date'+date) as r:
                try:
                    res = await r.json(content_type="text/html")
                except:
                     res = await r.json(content_type="application/javascript")


        embed = discord.Embed(title="__**" + res["date"] + "**__", colour=discord.Colour(0x277b0), url=res["url"], description="Necrobot is proud to present: **Births today in History**")
        embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

        for birth in random.sample(res["data"]["Births"], 15):
            try:
                embed.add_field(name="Year {}".format(birth["year"]), value="[{}]({})".format(birth["text"].replace("d.","Death: "), birth["links"][0]["link"]), inline=False)
            except AttributeError:
                pass


        await ctx.channel.send(embed=embed)

    def get_a_hero_stat(self, data, username, hero_int, hero_list):
        embed = discord.Embed(title="__**" + username + "**__", colour=discord.Colour(0x277b0), description=hero_list[hero_int].title())
        embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

        s = data["pc"]["us"]["stats"]["quickplay"][hero_list[hero_int]]

        # general stats
        stats = list()
        to_find = ["deaths", "medals", "weapon_accuracy", "all_damage_done", "kill_streak_best", "time_played", "games_won"]
        for x in to_find:
            try:
                title = x
                if "most" in x:
                    title = "Most " + x.replace("most_", "")

                stats.append(title.replace("_", " ").title() + ": " + "{0:.2f}".format(s["general_stats"][x]))
            except KeyError:
                pass

        embed.add_field(name="General Stats", value="-" + "\n-".join(stats), inline=False)

        # hero specific stats
        stats = list()
        for x in s["hero_stats"]:
            title = x
            if "most" in x:
                title = "Most " + x.replace("most_", "")

            stats.append(title.replace("_", " ").title() + ": " + "{0:.2f}".format(s["hero_stats"][x]))

        embed.add_field(name="Hero Stats", value="-" + "\n-".join(stats), inline=False)

        return embed


    @commands.command()
    async def ow(self, ctx, username):
        """Creates a rich embed of the user's Owerwatch stats for PC only. You must parse through a valid Battle.NET Battle Tag.

        {usage}

        __Example__
        `{pre}ow FakeTag#1234` - generates the embed for user FakeTag#1234"""
        hero_int = 0
        client = AsyncOWAPI()
        data = {}
        username = re.sub(" -", "#", username)
        msg = await ctx.channel.send("Gathering data...")

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            try:
                data[PC] = await client.get_profile(username, session=session, platform=PC)
                data[PC] = await client.get_stats(username, session=session, platform=PC)
                data[PC] = await client.get_achievements(username, session=session, platform=PC)
                data[PC] = await client.get_hero_stats(username, session=session, platform=PC)
            except asyncio.TimeoutError:
                await msg.edit('Time out error has occured. Please try again.')

        try:
            heroes = data["pc"]["us"]["stats"]["quickplay"]
            hero_list = list(data["pc"]["us"]["stats"]["quickplay"].keys())
        except KeyError:
            await ctx.channel.send("Something went terribly wrong", delete_after=10)
            return

        await msg.delete()
        msg = await ctx.channel.send(embed=self.get_a_hero_stat(data, username, hero_int, hero_list))

        while True:
            asyncio.sleep(1)
            react_list = list()
            if hero_int > 0:
                react_list.append("\N{BLACK LEFT-POINTING TRIANGLE}")

            react_list.append("\N{BLACK SQUARE FOR STOP}")

            if hero_int < len(hero_list) - 1:
                react_list.append("\N{BLACK RIGHT-POINTING TRIANGLE}")

            for reaction in react_list:
                await msg.add_reaction(reaction)

            def check(reaction, user):
                return reaction.message == msg and user == ctx.message.author.name and reaction in react_list

            res = await self.bot.wait_for("reaction_add", check=check, timeout=300)

            if res.reaction.emoji == "\N{BLACK SQUARE FOR STOP}":
                await msg.clear_reactions()
                break
            elif res.reaction.emoji == "\N{BLACK LEFT-POINTING TRIANGLE}":
                hero_int -= 1
            elif res.reaction.emoji == "\N{BLACK RIGHT-POINTING TRIANGLE}":
                hero_int += 1

            await msg.clear_reactions()
            await msg.edit_message(embed=self.get_a_hero_stat(data, username, hero_int, hero_list))
            asyncio.sleep(1)

    @commands.command(name="ud", aliases=["urbandictionary"])
    async def udict(self, ctx, word):
        """Searches for the given word on urban dictionnary

        {usage}

        __Example__
        `{pre}ud pimp` - searches for pimp on Urban dictionnary"""
        defs = ud.define(word)
        definition = defs[0]

        embed = discord.Embed(title="__**{}**__".format(word.title()), url="http://www.urbandictionary.com/", colour=discord.Colour(0x277b0), description=definition.definition)
        embed.add_field(name="__Examples__", value=definition.example)

        await ctx.message.send(embed=embed)

    @commands.command()
    async def translate(self, ctx, lang, *, sentence):
        """Auto detects the language of the setence you input and translates it to the desired language.

        {usage}

        __Example__
        `{pre}translate en Bonjour` - detects french and translates to english
        `{pre}translate ne Hello` - detects english and translates to dutch"""
        translated = translator.translate(sentence, dest=lang)
        await ctx.message.send("Translated `{0.origin}` from {0.src} to {0.dest}: **{0.text}**".format(translated))

    @commands.command()
    async def define(self, ctx, word):
        """Defines the given word

        {usage}

        __Example__
        `{pre}define sand` - defines the word sand
        `{pre}define life` - defines the word life"""
        meaning = await dictionary.meaning(word)
        if meaning is None:
            await ctx.message.send(":negative_squared_cross_mark: | **No definition found for this word**")
            return

        embed = discord.Embed(title="__**{}**__".format(word.title()), url="https://en.oxforddictionaries.com/", colour=discord.Colour(0x277b0), description="Information on this word")
        for x in meaning:
            embed.add_field(name=x, value="-" + "\n-".join(meaning[x]))

        await ctx.message.send(embed=embed)

def setup(bot):
    bot.add_cog(Utilities(bot))

