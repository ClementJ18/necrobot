#!/usr/bin/python3.6
#!/usr/bin/env python -W ignore::DeprecationWarning

import discord
from discord.ext import commands
from simpleeval import simple_eval
import time
import aiohttp
import random
import re
import json
import asyncio
import urbandictionary as ud
import googletrans
from PyDictionary import PyDictionary 
from bs4 import BeautifulSoup
import ast
from rings.utils.utils import has_perms

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
translator = googletrans.Translator()


class Utilities():
    """A bunch of useful commands to do various tasks."""
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}
        for guild in self.bot.guilds:
            self.queue[guild.id] = {"end": True, "list" : []}

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
        await pingms.edit(content=":white_check_mark: | The ping time is `% .01f seconds`" % ping)

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

        embed.add_field(name="**Members**", value=guild.member_count, inline=True)

        embed.add_field(name="**Region**", value=guild.region)
        embed.add_field(name="**Server ID**", value=guild.id, inline=True)

        channel_list = [channel.name for channel in guild.channels]
        channels = ", ".join(channel_list) if len(", ".join(channel_list)) < 1024 else ""
        role_list = [role.name for role in guild.roles]
        roles = ", ".join(role_list) if len(", ".join(role_list)) < 1024 else ""
        embed.add_field(name="**Channels**", value="{}: {}".format(len(channel_list), channels))
        embed.add_field(name="**Roles**", value="{}: {}".format(len(role_list), roles))

        await ctx.channel.send(embed=embed)

    @commands.command()
    async def avatar(self, ctx,* , user : discord.Member=None):
        """Returns a link to the given user's profile pic 
        
        {usage}
        
        __Example__
        `{pre}avatar @NecroBot` - return the link to NecroBot's avatar"""
        if user is None:
            user = ctx.message.author
        avatar = user.avatar_url_as(format="png")
        await ctx.channel.send(avatar)

    @commands.group(invoke_without_command = True)
    async def today(self, ctx, date : str = ""):
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
                    res = await r.json()
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
    async def today_deaths(self, ctx, date : str = ""):
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
                    res = await r.json()
                except:
                     res = await r.json(content_type="application/javascript")

        embed = discord.Embed(title="__**" + res["date"] + "**__", colour=discord.Colour(0x277b0), url=res["url"], description="Necrobot is proud to present: **Deaths today in History**")
        embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

        for death in random.sample(res["data"]["Deaths"], 10):
            try:
                embed.add_field(name="Year {}".format(death["year"]), value="[{}]({})".format(death["text"].replace("b.","Birth: "), death["links"][0]["link"]), inline=False)
            except AttributeError:
                pass

        await ctx.channel.send(embed=embed)


    @today.command(name="births")
    async def today_births(self, ctx, date : str = ""):
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
                    res = await r.json()
                except:
                     res = await r.json(content_type="application/javascript")


        embed = discord.Embed(title="__**" + res["date"] + "**__", colour=discord.Colour(0x277b0), url=res["url"], description="Necrobot is proud to present: **Births today in History**")
        embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

        for birth in random.sample(res["data"]["Births"], 10):
            try:
                embed.add_field(name="Year {}".format(birth["year"]), value="[{}]({})".format(birth["text"].replace("d.","Death: "), birth["links"][0]["link"]), inline=False)
            except AttributeError:
                pass


        await ctx.channel.send(embed=embed)

    @commands.command(name="ud", aliases=["urbandictionary"])
    async def udict(self, ctx, *, word : str):
        """Searches for the given word on urban dictionnary

        {usage}

        __Example__
        `{pre}ud pimp` - searches for pimp on Urban dictionnary"""
        try:
            defs = ud.define(word)
            definition = defs[0]
        except IndexError:
            await ctx.send(":negative_squared_cross_mark: | Sorry, I didn't find a definition for this word.")
            return

        embed = discord.Embed(title="__**{}**__".format(word.title()), url="http://www.urbandictionary.com/", colour=discord.Colour(0x277b0), description=definition.definition)
        embed.add_field(name="__Examples__", value=definition.example)

        await ctx.message.channel.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def translate(self, ctx, lang : str, *, sentence : str):
        """Auto detects the language of the setence you input and translates it to the desired language.

        {usage}

        __Example__
        `{pre}translate en Bonjour` - detects french and translates to english
        `{pre}translate ne Hello` - detects english and translates to dutch"""
        try:
            translated = translator.translate(sentence, dest=lang)
            await ctx.message.channel.send("Translated `{0.origin}` from {0.src} to {0.dest}: **{0.text}**".format(translated))
        except ValueError:
            await ctx.message.channel.send(":negative_squared_cross_mark: | No such language, do `n!translate list` for all languages (Warning: Big text blob)")
    
    @translate.command(name="list")
    async def translate_list(self, ctx):
        text = ""
        for lang in googletrans.LANGUAGES:
            text += "**{}**: {}, ".format(googletrans.LANGUAGES[lang], lang)

        await ctx.send(text[:-2])

    @commands.command()
    async def define(self, ctx, word : str):
        """Defines the given word

        {usage}

        __Example__
        `{pre}define sand` - defines the word sand
        `{pre}define life` - defines the word life"""
        meaning = await dictionary.meaning(word)
        if meaning is None:
            await ctx.message.channel.send(":negative_squared_cross_mark: | **No definition found for this word**")
            return

        embed = discord.Embed(title="__**{}**__".format(word.title()), url="https://en.oxforddictionaries.com/", colour=discord.Colour(0x277b0), description="Information on this word")
        for x in meaning:
            embed.add_field(name=x, value="-" + "\n-".join(meaning[x]))

        await ctx.message.channel.send(embed=embed)

    @commands.command()
    async def ow(self, ctx, username, region="eu", hero=None):
        """Creates a rich embed of the user's Owerwatch stats for PC only. You must parse through a valid Battle.NET Battle 
        Tag. You can also optionally parse in a hero's name to start the embeds at this hero.


        {usage}


        __Example__
        `{pre}ow FakeTag#1234 us` - generates an embed for user FakeTag#1234 in region us
        `{pre}ow FakeTag#0000 eu Winston` - generates an embed for user FakeTag#0000 in region eu starting at winston"""
        def get_a_hero_stat():
            prog_list = ["__**"+hero.title()+"**__" if hero_list.index(hero) == hero_int else hero.title() for hero in hero_list]
            prog = " - ".join(prog_list)
            embed = discord.Embed(title="**" + username.replace("-", "#") + "** in region: " + region.upper(), colour=discord.Colour(0x277b0), description=prog)
            embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

            s = data[region]["heroes"]["stats"]["quickplay"][hero_list[hero_int]]

            # general stats
            stats = list()
            to_find = ["deaths", "medals", "weapon_accuracy", "all_damage_done", "kill_streak_best", "time_played", "games_won"]
            for stat in to_find:
                try:
                    title = stat
                    if "most" in stat:
                        title = "Most " + stat.replace("most_", "")
                    stats.append(title.replace("_", " ").title() + ": " + "{0:.2f}".format(s["general_stats"][stat]))
                except KeyError:
                    pass

            embed.add_field(name="General Stats", value="-" + "\n-".join(stats), inline=False)

            # hero specific stats
            stats = list()
            for stat in s["hero_stats"]:
                title = stat
                if "most" in stat:
                    title = "Most " + stat.replace("most_", "")

                stats.append(title.replace("_", " ").title() + ": " + "{0:.2f}".format(s["hero_stats"][stat]))

            embed.add_field(name="Hero Stats", value="-" + "\n-".join(stats), inline=False)

            return embed

        async with ctx.message.channel.typing():
            username = username.replace("#", "-")
            headers = {"User-Agent":"NecroBot"}
            async with aiohttp.ClientSession() as cs:
                async with cs.get("https://owapi.net/api/v3/u/{}/heroes".format(username), headers=headers) as r:
                    data = await r.json()

            hero_list = list(data[region]["heroes"]["stats"]["quickplay"].keys())

            if hero == None:
                hero_int = 0
            else:
                try:
                    hero_int = hero_list.index(hero.lower())
                except:
                    hero_int = 0

            msg = await ctx.message.channel.send(embed=get_a_hero_stat())

        while True:
            react_list = list()
            if hero_int > 0:
                react_list.append("\N{BLACK LEFT-POINTING TRIANGLE}")

            react_list.append("\N{BLACK SQUARE FOR STOP}")

            if hero_int < len(hero_list) - 1:
                react_list.append("\N{BLACK RIGHT-POINTING TRIANGLE}")

            for reaction in react_list:
                await msg.add_reaction(reaction)

            def check(reaction, user):
                return user == ctx.message.author and str(reaction.emoji) in react_list and msg.id == reaction.message.id

            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=300)
            except asyncio.TimeoutError:
                return

            if reaction.emoji == "\N{BLACK SQUARE FOR STOP}":
                await msg.clear_reactions()
                break
            elif reaction.emoji == "\N{BLACK LEFT-POINTING TRIANGLE}":
                hero_int -= 1
            elif reaction.emoji == "\N{BLACK RIGHT-POINTING TRIANGLE}":
                hero_int += 1

            await msg.clear_reactions()
            await msg.edit(embed=get_a_hero_stat())

    @commands.command(enabled=False)
    async def reminder(self, ctx, *, message):
        """Creates a reminder in seconds. Doesn't work at the moment.

        {usage}

        __Examples__
        `{pre}reminder do the dishes in 40` - will remind you to do the dishes in 40 seconds"""
        if "in" not in message:
            await ctx.send(":negative_squared_cross_mark: | Something went wrong, you need to use the format <message> in <time>")

        text = message.split(" in ")[0]
        time =int(message.split(" in ")[1])
        await ctx.send(":white_check_mark: | Okay I will remind you in **{}** seconds of **{}**".format(time, text))

        await asyncio.sleep(time)

        await ctx.send(":alarm_clock: | You asked to be reminded: **{}**".format(text))

    @commands.group(invoke_without_command=True)
    async def q(self, ctx):
        """Displays the content of the queue at the moment.

        {usage}"""
        if len(self.queue[ctx.guild.id]["list"]) > 0:
            queue = ["**" + ctx.guild.get_member(x).display_name + "**" for x in self.queue[ctx.guild.id]["list"]]
            await ctx.send("So far the queue has the following users in it:\n-{}".format("\n-".join(queue)))
        else:
            await ctx.send("So far this queue has no users in it.")

    @q.command(name="start")
    @has_perms(2)
    async def q_start(self, ctx):
        """Starts a queue, if there is already an ongoing queue it will fail. The ongoing queue must be cleared first using `{pre}q clear`.

        {usage}"""
        if len(self.queue[ctx.guild.id]["list"]) > 0:
            await ctx.send(":negative_squared_cross_mark: | A queue is already ongoing, please clear the queu first")
            return

        self.queue[ctx.guild.id] = {"end": False, "list" : []}
        await ctx.send(":white_check_mark: | Queue initialized")

    @q.command(name="end")
    @has_perms(2)
    async def q_end(self, ctx):
        """Ends a queue but does not clear it. Users will no longer be able to use `{pre}q me`

        {usage}"""
        self.queue[ctx.guild.id]["end"] = True
        await ctx.send(":white_check_mark: | Users will now not be able to add themselves to queue")

    @q.command(name="clear")
    @has_perms(2)
    async def q_clear(self, ctx):
        """Ends a queue and clears it. Users will no longer be able to add themselves and the content of the queue will be 
        emptied. Use it in order to start a new queue

        {usage}"""
        self.queue[ctx.guild.id]["list"] = []
        self.queue[ctx.guild.id]["end"] = True
        await ctx.send(":white_check_mark: | Queue cleared and ended. Please start a new queue to be able to add users again")

    @q.command(name="me")
    async def q_me(self, ctx):
        """Queue the user that used the command to the current queue. Will fail if queue has been ended or cleared.

        {usage}"""
        if self.queue[ctx.guild.id]["end"]:
            await ctx.send(":negative_squared_cross_mark: | Sorry, you can no longer add yourself to the queue")
            return

        if ctx.author.id in self.queue[ctx.guild.id]["list"]:
            await ctx.send(":white_check_mark: | You have been removed from the queue")
            self.queue[ctx.guild.id]["list"].remove(ctx.author.id)
            return

        self.queue[ctx.guild.id]["list"].append(ctx.author.id)
        await ctx.send(":white_check_mark: |  You have been added to the queue")

    @q.command(name="next")
    @has_perms(2)
    async def q_next(self, ctx):
        """Mentions the next user and the one after that so they can get ready.
        
        {usage}"""
        if len(self.queue[ctx.guild.id]["list"]) < 1:
            await ctx.send(":negative_squared_cross_mark: | No users left in that queue")
            return

        msg = ":bell: | {}, you're next. Get ready!".format(ctx.guild.get_member(self.queue[ctx.guild.id]["list"][0]).mention)

        if len(self.queue[ctx.guild.id]["list"]) > 1:
            msg += " \n{}, you're right after them. Start warming up!".format(ctx.guild.get_member(self.queue[ctx.guild.id]["list"][1]).mention)
        else:
            msg += "\nThat's the last user in the queue"

        await ctx.send(msg)
        self.queue[ctx.guild.id]["list"].pop(0)

    # @commands.command(aliases=["tz"])
    # async def timezone(self, ctx, time, origin_tz, convert_tz):
    #     hour, minute = time.split(":")
    #     datetime_obj = timedelta(hour=hour, minute=minute)
    #     datetime_obj_utc = datetime_obj.replace(tzinfo=timezone(origin_tz))

def setup(bot):
    bot.add_cog(Utilities(bot))

