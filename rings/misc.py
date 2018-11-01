import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from rings.utils.utils import react_menu
from rings.utils.hunger_game import events

import random
import asyncio
import aiohttp
import traceback

class Misc():
    """A cog for all bunch commands that don't have a specific category they can stick to."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def fight(self, ctx, *, tributes):
        """Takes in a list of tributes separated by `,` and simulates a hunger games based on Bransteele's Hunger Game 
        Simulator. More than one tribute needs to be supplied. Duplicate names will be supressed.

        {usage}

        __Example__
        `{pre}fight john , bob , emilia the trap` - starts a battle between tributes john, bob and emilia the trap"""
        tributes_list = list(set([x.strip() for x in tributes.split(",")]))
        if len(tributes_list) < 2:
            await ctx.send(":negative_squared_cross_mark: | Please provide at least two names separated by `,`")
            return

        if len(tributes_list) > 32:
            await ctx.send(":negative_squared_cross_mark: | Please provide no more than 32 characters separated by `,`.")

        dead_list = []

        async def _phase_parser(event_name):
            idle_tributes = tributes_list.copy()
            # idle_events = events[event_name].copy()
            deathless = [event for event in events[event_name] if len(event["killed"]) < 1]
            idle_events = events[event_name].copy() + deathless.copy() #2 times the amount of not deadly events reduces possibility of picking deadly to 1/3th
            embed = discord.Embed(title="__**Hunger Games Simulator**__", colour=discord.Colour(0x277b0), description=f"{' - '.join(tributes_list)}\nPress :arrow_forward: to proceed")
            embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))

            done_list = list()
            while idle_tributes and len(tributes_list) > 1:
                tributes = list()
                event = random.choice([event for event in idle_events if event["tributes"] <= len(idle_tributes) and len(event["killed"]) < len(tributes_list)])
                tributes = random.sample(idle_tributes, event["tributes"])
                idle_tributes = [x for x in idle_tributes if x not in tributes]
                if event["killed"]:
                    for killed in event["killed"]:
                        tribute = tributes[int(killed)-1]
                        del tributes_list[tributes_list.index(tribute)]
                        dead_list.append(tribute)

                format_dict = dict()
                for tribute in tributes:
                    format_dict["p"+str(tributes.index(tribute)+1)] = tribute
                try:
                    done_list.append(event["string"].format(**format_dict))
                except Exception as e:
                    channel = self.bot.get_channel(415169176693506048)
                    the_traceback = f"```py\n{traceback.format_exc()}\n```"
                    embed = discord.Embed(title="Fight Error", description=the_traceback, colour=discord.Colour(0x277b0))
                    embed.add_field(name='Error String', value=event["string"])
                    embed.add_field(name='Error Tribute Number', value=event["tributes"])
                    embed.add_field(name='Error Tribute Killed', value=event["killed"])
                    embed.add_field(name='Error Tributes', value=str(format_dict))
                    embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
                    await channel.send(embed=embed)

                    if ctx.guild.id != 311630847969198082:
                        await ctx.send(":negative_squared_cross_mark: | Something unexpected went wrong, Necro's gonna get right to it. If you wish to know more on what went wrong you can join the support server: <https://discord.gg/Ape8bZt>")

                    return

            embed.add_field(name=f"{event_name.title()} {day}", value="\n".join(done_list))
            return embed            
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "\N{BLACK RIGHT-POINTING TRIANGLE}" and msg.id == reaction.message.id

        day = 0
        embed = await _phase_parser("bloodbath")
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("\N{BLACK RIGHT-POINTING TRIANGLE}")
        await self.bot.wait_for("reaction_add", check=check, timeout=600)

        async def _event_parser(event):
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == "\N{BLACK RIGHT-POINTING TRIANGLE}" and msg.id == reaction.message.id

            embed = await _phase_parser(event)
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("\N{BLACK RIGHT-POINTING TRIANGLE}")
            try:
                await self.bot.wait_for("reaction_add", check=check, timeout=600)
            except asyncio.TimeoutError as e:
                e.timer = 600
                await msg.clear_reactions()
                return self.bot.dispatch("command_error",ctx, e)

        while len(tributes_list) > 1:

            if day == 6:
                await _event_parser("feast")

            if len(tributes_list) >1: 
                await _event_parser("day")

            embed = discord.Embed(title="__**Dead Tributes**__", description="- " + "\n- ".join(dead_list) if dead_list else "None")
            embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("\N{BLACK RIGHT-POINTING TRIANGLE}")

            try:
                await self.bot.wait_for("reaction_add", check=check, timeout=600)
            except asyncio.TimeoutError as e:
                e.timer = 600
                await msg.clear_reactions()
                return self.bot.dispatch("command_error", ctx, e)
            dead_list = []

            if len(tributes_list) >1: 
                await _event_parser("night")

            day += 1

        embed = discord.Embed(title="Hunger Game Winner", description=f":tada:{tributes_list[0]} is the Winner! :tada:", colour=discord.Colour(0x277b0))
        embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
        await ctx.send(embed=embed) 


    @commands.command()
    async def ow(self, ctx, username, region="eu", hero=None):
        """Creates a rich embed of the user's Owerwatch stats for PC only. You must parse through a valid Battle.NET Battle 
        Tag and optionally a region. You can also optionally parse in a hero's name to start the embeds at this hero.


        {usage}


        __Example__
        `{pre}ow FakeTag#1234 us` - generates an embed for user FakeTag#1234 in region us
        `{pre}ow FakeTag#0000 eu Winston` - generates an embed for user FakeTag#0000 in region eu starting at winston"""
        def get_a_hero_stat(hero_int):
            prog_list = ["__**"+hero.title()+"**__" if hero_list.index(hero) == hero_int else hero.title() for hero in hero_list]
            prog = " - ".join(prog_list)
            embed = discord.Embed(title="**" + username.replace("-", "#") + "** in region: " + region.upper(), colour=discord.Colour(0x277b0), description=prog)
            embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))

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
            async with self.bot.session.get(f"https://owapi.net/api/v3/u/{username}/heroes", headers=headers) as r:
                try:
                    data = await r.json()
                except Exception:
                    return

            hero_list = list(data[region]["heroes"]["stats"]["quickplay"].keys())

            if not hero:
                hero_int = 0
            else:
                try:
                    hero_int = hero_list.index(hero.lower())
                except IndexError:
                    hero_int = 0

        await react_menu(ctx, len(hero_list)-1, get_a_hero_stat, hero_int)

    @commands.command()
    @commands.cooldown(3, 5, BucketType.channel)
    async def cat(self, ctx):
        """Posts a random cat picture from random.cat
        
        {usage}"""
        async with self.bot.session.get('http://aws.random.cat/meow') as r:
            try:
                res = await r.json()
                await ctx.send(embed=discord.Embed().set_image(url=res['file']))
                self.bot.cat_cache.append(res["file"])
            except aiohttp.ClientResponseError:
                if self.bot.cat_cache:
                    await ctx.send("API overloading, have a cached picture instead.", embed=discord.Embed(colour=discord.Colour(0x277b0)).set_image(url=random.choice(self.bot.cat_cache)))
                else:
                    await ctx.send(":negative_squared_cross_mark: | API overloading and cache empty, looks like you'll have to wait for now.")

    @commands.command()
    async def dog(self, ctx):
        """Posts a random dog picture from random.dog 
        
        {usage}"""
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as cs:
            async with cs.get('https://random.dog/woof.json') as r:
                res = await r.json()
                await ctx.send(embed=discord.Embed().set_image(url=res['url']))

def setup(bot):
    bot.add_cog(Misc(bot))
