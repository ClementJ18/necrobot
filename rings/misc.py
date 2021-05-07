import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from rings.utils.utils import react_menu, BotError, guild_only
from rings.utils.hunger_game import events

import re
import random
import asyncio
import aiohttp
import traceback

class FightError(Exception):
    def __init__(self, message, event = None, format_dict = None):
        super().__init__(message)
        
        self.message = message
        self.event = event
        self.format_dict = format_dict
        
    def embed(self, bot):
        error_traceback = f"```py\n{traceback.format_exc()}\n```"
        embed = discord.Embed(title="Fight Error", description=error_traceback, colour=discord.Colour(0x277b0))
        embed.add_field(name='Error String', value=self.event["string"], inline=False)
        embed.add_field(name='Error Tribute Number', value=self.event["tributes"], inline=False)
        embed.add_field(name='Error Tribute Killed', value=self.event["killed"], inline=False)
        embed.add_field(name='Error Tributes', value=str(self.format_dict), inline=False)
        embed.set_footer(text="Generated by Necrobot", icon_url=bot.user.avatar_url_as(format="png", size=128))
        
        return embed

class StopError(Exception):
    pass
        
class HungerGames:
    def __init__(self, tributes, ctx):
        self.tributes = tributes
        self.day = 1
        self.dead = []
        self.ctx = ctx
    
    async def wait_for_next_phase(self, msg):
        reactions = ["\N{BLACK SQUARE FOR STOP}", "\N{BLACK RIGHT-POINTING TRIANGLE}"]
        
        def check(reaction, user):
            return user == self.ctx.author and str(reaction.emoji) in reactions and msg.id == reaction.message.id

        for reaction in reactions:
            await msg.add_reaction(reaction)
        
        reaction, _ = await self.ctx.bot.wait_for(
            "reaction_add", 
            check=check, 
            timeout=600, 
            handler=msg.clear_reactions, 
            propagate=True
        )
        
        if reaction.emoji == "\N{BLACK SQUARE FOR STOP}":
            await msg.clear_reactions()
            raise StopError()
            
        await msg.clear_reactions()
        
    async def prepare_next_phase(self, event_name):
        idle_tributes = self.tributes.copy()
        
        deathless = [event for event in events[event_name] if len(event["killed"]) < 1]
        idle_events = events[event_name].copy() + deathless.copy()
        
        embed = discord.Embed(
            title="Hunger Games Simulator", 
            colour=discord.Colour(0x277b0), 
            description=f"{' - '.join(self.tributes)}\nPress :arrow_forward: to proceed"
        )
            
        embed.set_footer(text="Generated by Necrobot", icon_url=self.ctx.bot.user.avatar_url_as(format="png", size=128))
        
        done_events = []
        while idle_tributes and len(self.tributes) > 1:
            tributes = []
            event = random.choice([event for event in idle_events if event["tributes"] <= len(idle_tributes) and len(event["killed"]) < len(self.tributes)])
            tributes = random.sample(idle_tributes, event["tributes"])
            idle_tributes = [x for x in idle_tributes if x not in tributes]
            if event["killed"]:
                for killed in event["killed"]:
                    tribute = tributes[int(killed)-1]
                    self.tributes.remove(tribute)
                    self.dead.append(tribute)
                    
            format_dict = {}
            for tribute in tributes:
                format_dict["p"+str(tributes.index(tribute)+1)] = tribute
            
            try:
                done_events.append(event["string"].format(**format_dict))
            except:
                raise FightError("Error formatting event", event, format_dict)

        embed.add_field(name=f"{event_name.title()} {self.day}", value="\n".join(done_events), inline=False)
        return embed  
            
    async def process_deads(self):
        embed = discord.Embed(title="Dead Tributes", description="- " + "\n- ".join(self.dead) if self.dead else "None")
        embed.set_footer(text="Generated by Necrobot", icon_url=self.ctx.bot.user.avatar_url_as(format="png", size=128))
        self.dead = []
        
        return embed
         
    async def loop(self):
        msg = await self.ctx.send(embed=await self.prepare_next_phase("bloodbath"))
        await self.wait_for_next_phase(msg)

        while len(self.tributes) > 1:
            if self.day % 7 == 0:
                msg = await self.ctx.send(embed=await self.prepare_next_phase("feast"))
                await self.wait_for_next_phase(msg)
                
            if len(self.tributes) > 1:
                msg = await self.ctx.send(embed=await self.prepare_next_phase("day"))
                await self.wait_for_next_phase(msg)
                
            msg = await self.ctx.send(embed=await self.process_deads())
            await self.wait_for_next_phase(msg)
            
            if len(self.tributes) > 1:
                msg = await self.ctx.send(embed=await self.prepare_next_phase("night"))
                await self.wait_for_next_phase(msg)
                
            self.day += 1
            
        embed = discord.Embed(
            title="Hunger Game Winner", 
            description=f":tada: {self.tributes[0]} is the Winner! :tada:", 
            colour=discord.Colour(0x277b0)
        )
        embed.set_footer(text="Generated by Necrobot", icon_url=self.ctx.bot.user.avatar_url_as(format="png", size=128))
        await self.ctx.send(embed=embed)
            
class Misc(commands.Cog):
    """A cog for all bunch commands that don't have a specific category they can stick to."""
    def __init__(self, bot):
        self.bot = bot

    #######################################################################
    ## Functions
    #######################################################################

    async def setup_table(self):
        for faction in self.bot.settings["messages"]["factions"]:
            for enemy in self.bot.settings["messages"]["factions"]:
                await self.bot.db.query_executer(
                    "INSERT INTO necrobot.InternalRanked VALUES ($1, $2, 0, 0) ON CONFLICT DO NOTHING",
                    faction, enemy 
                )

        
    #######################################################################
    ## Commands
    #######################################################################
        
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
                    raise BotError("API overloading and cache empty, looks like you'll have to wait for now.")

    @commands.command()
    async def dog(self, ctx):
        """Posts a random dog picture from random.dog 
        
        {usage}"""
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as cs:
            async with cs.get('https://random.dog/woof.json') as r:
                res = await r.json()
                await ctx.send(embed=discord.Embed().set_image(url=res['url']))        
                
    @commands.command()
    async def fight(self, ctx, *, tributes):
        """Takes in a list of tributes separated by `,` and simulates a hunger games based on Bransteele's Hunger Game 
        Simulator. More than one tribute needs to be supplied. Duplicate names will be supressed.

        {usage}

        __Example__
        `{pre}fight john , bob , emilia the trap` - starts a battle between tributes john, bob and emilia the trap"""
        tributes_list = list(set([f"**{x.strip()}**" for x in tributes.split(",")]))
        if len(tributes_list) < 2:
            await ctx.send(":negative_squared_cross_mark: | Please provide at least two names separated by `,`")
            return

        if len(tributes_list) > 32:
            await ctx.send(":negative_squared_cross_mark: | Please provide no more than 32 names separated by `,`.")
            
        hg = HungerGames(tributes_list, ctx)
        try:
            await hg.loop()
        except StopError:
            pass

    @commands.command()
    @guild_only(496617962334060545)
    async def matchups(self, ctx, **string):
        """Get data about the results of matchups stored in the bot
        
        {usage}

        """
        def embed_maker(index, entries):
            description = ""
            for entry in entries:
                description += f"**{entry[1]}** - {entry[3]} : {entry[3]+entry[2]} ({entry[3]/entry[3]+entry[2]}%)\n"

            embed = discord.Embed(title=entries[0][0], description=description, colour=discord.Colour(0x277b0))
            embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
            return embed

        if string:
            regex = r"(gondor|rohan|isengard|mordor|ered luin|angmar|erebor|iron hills|lothlorien|imladris|misty mountains)"
            factions = re.findall(regex, string.lower())

            if not factions:
                raise BotError("Could not find a faction in the arguments")

            faction = factions[0]
            if len(factions) > 1:
                enemies = factions[1:]
                stats = await self.bot.db.query_executer(
                    "SELECT * FROM necrobot.InternalRanked WHERE faction = $1 AND enemy = ANY($2) ORDER BY enemy",
                    faction, enemies
                )
            else:
                stats = await self.bot.db.query_executer(
                    "SELECT * FROM necrobot.InternalRanked WHERE faction = $1 ORDER BY enemy",
                    faction
                )

            await ctx.send(embed=embed_maker(None, stats))
        else:
            stats = await self.bot.db.query_executer(
                    "SELECT * FROM necrobot.InternalRanked GROUP BY faction ORDER BY enemy"
                )

            await react_menu(ctx, stats, 1, embed_maker)

    #######################################################################
    ## Events
    #######################################################################

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id != 840220523865702400:
            return

        if not payload.emoji.is_custom_emoji():
            return
        
        if payload.message_id in self.settings["messages"]["defeats"]:
            index = "defeats"
        elif payload.message_id in self.settings["messages"]["victories"]:
            index = "victories"
        else:
            return


        faction_index = self.settings["messages"][index].index(payload.message_id)
        faction_name = self.settings["messages"]["factions"][faction_index]

        enemy_index = self.settings["messages"]["emotes"].index(payload.message_id)
        enemy_name = self.settings["messages"]["factions"][enemy_index]

        def check(pay):
            return pay.user_id == payload.user_id and pay.message_id == payload.message_id and payload.emoji == "\N{WHITE HEAVY CHECK MARK}"

        try:
            checkmark = await self.bot.wait_for("on_raw_reaction_add", check=check, timeout=15)
        except asyncio.TimeoutError:
            return await self.bot._http.remove_reaction(payload.channel_id, payload.message_id, payload.emoji._as_reaction(), payload.user_id)

        await asyncio.sleep(2)
        await self.bot.query_executer(
            f"UPDATE necrobot.InternalRanked SET {index} = {index} + 1 WHERE faction = $1 AND enemy = $2",
            faction_name, enemy_name
        )
        await self.bot._http.remove_reaction(payload.channel_id, payload.message_id, payload.emoji._as_reaction(), payload.user_id)
        await self.bot._http.remove_reaction(payload.channel_id, payload.message_id, checkmark.emoji._as_reaction(), payload.user_id)


def setup(bot):
    bot.add_cog(Misc(bot))
