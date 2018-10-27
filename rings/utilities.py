import discord
from discord.ext import commands

from rings.utils.utils import has_perms, react_menu, TimeConverter

import random
import asyncio
from simpleeval import simple_eval

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
            await ctx.send(f":1234: | **{final}**")
        except NameError:
            await ctx.send(":negative_squared_cross_mark: | **Mathematical equation not recognized.**")

    @commands.command(aliases=["pong"])
    async def ping(self, ctx):
        """Pings the user and returns the time it took. 
        
        {usage}"""
        await ctx.send(f'Pong! That took {self.bot.latency * 1000} seconds.')

    @commands.command()
    @commands.guild_only()
    async def serverinfo(self, ctx):
        """Returns a rich embed of the server's information. 
        
        {usage}"""
        guild = ctx.message.guild
        embed = discord.Embed(title=f"__**{guild.name}**__", colour=discord.Colour(0x277b0), description="Info on this server")
        embed.set_thumbnail(url=guild.icon_url.replace("webp","jpg"))
        embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")

        embed.add_field(name="**Date Created**", value=guild.created_at.strftime("%d - %B - %Y %H:%M"))
        embed.add_field(name="**Owner**", value=str(guild.owner), inline=True)

        embed.add_field(name="**Members**", value=guild.member_count, inline=True)

        embed.add_field(name="**Region**", value=guild.region)
        embed.add_field(name="**Server ID**", value=guild.id, inline=True)

        channel_list = [channel.name for channel in guild.channels]
        channels = ", ".join(channel_list) if len(", ".join(channel_list)) < 1024 else ""
        role_list = [role.name for role in guild.roles]
        roles = ", ".join(role_list) if len(", ".join(role_list)) < 1024 else ""
        embed.add_field(name="**Channels**", value=f"{len(channel_list)}: {channels}")
        embed.add_field(name="**Roles**", value=f"{len(role_list)}: {roles}")

        await ctx.send(embed=embed)

    @commands.command()
    async def avatar(self, ctx,* , user : discord.Member=None):
        """Returns a link to the given user's profile pic 
        
        {usage}
        
        __Example__
        `{pre}avatar @NecroBot` - return the link to NecroBot's avatar"""
        if user is None:
            user = ctx.author

        avatar = user.avatar_url_as(format="png")
        await ctx.send(embed=discord.Embed().set_image(url=avatar))

    @commands.command()
    async def today(self, ctx, choice : str = None, date : str = None):
        """Creates a rich information about events/deaths/births that happened today or any day you indicate using the 
        `dd/mm` format. The choice argument can be either `events`, `deaths` or `births`.

        {usage}

        __Example__
        `{pre}today` - prints five events/deaths/births that happened today
        `{pre}today 14/02` - prints five events/deaths/births that happened on the 14th of February
        `{pre}today events` - prints five events that happened today
        `{pre}today events 14/02` - prints five events that happened on the 14th of February
        `{pre}today deaths` - prints deaths that happened today
        `{pre}today deaths 14/02` - prints deaths that happened on the 14th of February
        `{pre}today births` - prints births that happened today
        `{pre}today births 14/02` - prints births that happened on the 14th of February"""

        if date:
            r_date = date.split("/")
            date = f"/{r_date[1]}/{r_date[0]}"
        else:
            date = ""

        if choice:
            choice = choice.lower().title()
        else:
            choice = random.choice(["Deaths", "Births", "Events"])

        if not choice in ["Deaths", "Births", "Events"]:
            await ctx.send(":negative_squared_cross_mark: | Not a correct choice. Correct choices are `Deaths`, `Births` or `Events`.")
            return

        async with self.bot.session.get(f'http://history.muffinlabs.com/date{date}') as r:
            try:
                res = await r.json()
            except:
                 res = await r.json(content_type="application/javascript")

        def _embed_generator(index):
            embed = discord.Embed(title=f"__**{res['date']}**__", colour=discord.Colour(0x277b0), url=res["url"], description=f"Necrobot is proud to present: **{choice} today in History**\n Page {index+1}/{len(res['data'][choice])//5+1}")
            embed.set_footer(text="Generated by NecroBot", icon_url="https://cdn.discordapp.com/avatars/317619283377258497/a491c1fb5395e699148fcfed2ee755cf.jpg?size=128")
            for event in res["data"][choice][5*index:(index+1)*5]:
                try:
                    if choice == "Events":
                        link_list = "".join(["\n-[{}]({})".format(x["title"], x["link"]) for x in event["links"]])
                        embed.add_field(name=f"Year {event['year']}", value="{}\n__Links__{}".format(event['text'], link_list), inline=False)
                    elif choice == "Deaths":
                        embed.add_field(name=f"Year {event['year']}", value=f"[{event['text'].replace('b.','Birth: ')}]({event['links'][0]['link']})", inline=False)
                    elif choice == "Births":
                        embed.add_field(name=f"Year {event['year']}", value=f"[{event['text'].replace('d.','Death: ')}]({event['links'][0]['link']})", inline=False)
                except AttributeError:
                    pass

            return embed

        random.shuffle(res["data"][choice])
        await react_menu(self.bot, ctx, len(res["data"][choice])//5, _embed_generator)

    @commands.command()
    async def remindme(self, ctx, *, message):
        """Creates a reminder in seconds. The following times can be used: days (d), 
        hours (h), minutes (m), seconds (s).

        {usage}

        __Examples__
        `{pre}remindme do the dishes in 40s` - will remind you to do the dishes in 40 seconds
        `{pre}remindme do the dishes in 2m` - will remind you to do the dishes in 2 minutes
        `{pre}remindme do the dishes in 4d2h45m` - will remind you to do the dishes in 4 days, 2 hours and 45 minutes
        """
        if "in" not in message:
            await ctx.send(":negative_squared_cross_mark: | Something went wrong, you need to use the format <message> in <time>")

        text = message.split(" in ")[0]
        time = message.split(" in ")[1]
        sleep = await TimeConverter().convert(ctx, time)
        await ctx.send(f":white_check_mark: | Okay I will remind you in **{time}** of **{text}**")

        await asyncio.sleep(sleep)

        await ctx.send(f":alarm_clock: | You asked to be reminded: **{text}**")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def q(self, ctx):
        """Displays the content of the queue at the moment. Queue are shortlive instances, do not use them to
        hold data for extended periods of time. A queue should atmost only last a couple of days.

        {usage}"""
        if len(self.queue[ctx.guild.id]["list"]) > 0:
            queue = [f"**{ctx.guild.get_member(x).display_name}**" for x in self.queue[ctx.guild.id]["list"]]
            await ctx.send("So far the queue has the following users in it:\n-{}".format('\n-'.join(queue)))
        else:
            await ctx.send("So far this queue has no users in it.")

    @q.command(name="start")
    @commands.guild_only()
    @has_perms(2)
    async def q_start(self, ctx):
        """Starts a queue, if there is already an ongoing queue it will fail. The ongoing queue must be cleared first 
        using `{pre}q clear`.

        {usage}"""
        if len(self.queue[ctx.guild.id]["list"]) > 0:
            await ctx.send(":negative_squared_cross_mark: | A queue is already ongoing, please clear the queue first")
            return

        self.queue[ctx.guild.id] = {"end": False, "list" : []}
        await ctx.send(":white_check_mark: | Queue initialized")

    @q.command(name="end")
    @commands.guild_only()
    @has_perms(2)
    async def q_end(self, ctx):
        """Ends a queue but does not clear it. Users will no longer be able to use `{pre}q me`

        {usage}"""
        self.queue[ctx.guild.id]["end"] = True
        await ctx.send(":white_check_mark: | Users will now not be able to add themselves to queue")

    @q.command(name="clear")
    @commands.guild_only()
    @has_perms(2)
    async def q_clear(self, ctx):
        """Ends a queue and clears it. Users will no longer be able to add themselves and the content of the queue will be 
        emptied. Use it in order to start a new queue

        {usage}"""
        self.queue[ctx.guild.id]["list"] = []
        self.queue[ctx.guild.id]["end"] = True
        await ctx.send(":white_check_mark: | Queue cleared and ended. Please start a new queue to be able to add users again")

    @q.command(name="me")
    @commands.guild_only()
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
    @commands.guild_only()
    @has_perms(2)
    async def q_next(self, ctx):
        """Mentions the next user and the one after that so they can get ready.
        
        {usage}"""
        if len(self.queue[ctx.guild.id]["list"]) < 1:
            await ctx.send(":negative_squared_cross_mark: | No users left in that queue")
            return

        msg = f":bell: | {ctx.guild.get_member(self.queue[ctx.guild.id]['list'][0]).mention}, you're next. Get ready!"

        if len(self.queue[ctx.guild.id]["list"]) > 1:
            msg += f" \n{ctx.guild.get_member(self.queue[ctx.guild.id]['list'][1]).mention}, you're right after them. Start warming up!"
        else:
            msg += "\nThat's the last user in the queue"

        await ctx.send(msg)
        self.queue[ctx.guild.id]["list"].pop(0)

    @commands.command()
    async def convert(self, ctx, measure : float, symbol, conversion = None):
        """The ultimate conversion tool to breach the gap with America/UK and the rest of the world. Can convert most metric
        units to imperial and most imperial units to metric. This works for lenght, temperature and mass measures.

        {usage}

        __Example__
        `{pre}convert 10 ft m` - convert 10 feet into meters
        `{pre}convert 5 km in`  - convert 5 kilometers to inches"""
        def m_to_i(measure, symbol, conversion):
            index = m_values.index(symbol)
            measure *= (100**(index)) #convert to milimiters
            measure /= 25.4 #convert to inches

            #convert to requested imperial
            index = i_values.index(conversion)
            for value in i_conver[index:]:
                measure /= value

            return measure

        def i_to_m(measure, symbol, conversion):
            index = i_values.index(symbol)
            for value in i_conver[index:]:
                measure *= value

            measure *= 25.4 # converter to milimiters
            index = m_values.index(conversion)
            measure /= (100**(index))#convert to requested metric

            return measure

        def temp(f=None, c=None):
            if c:
                return c * 9/5 + 32

            if f:
                return (f - 32) * 5/9

        def mass_i_to_m(measure, symbol, conversion):
            #convert to oz
            index = mass_i_values.index(symbol)
            for value in mass_i_conver[index:]:
                measure = measure * value

            measure = measure * 28349.5 #convert to miligrams
            index = mass_m_values.index(conversion)
            measure /= (100**(index+1)) #convert to requested imperial

            return measure

        def mass_m_to_i(measure, symbol, conversion):
            index = mass_m_values.index(symbol)
            measure *= (100**(index+1)) # convert to miligrams
            measure = measure / 28349.5 #convert to oz

            #convert to requested imperial
            index = mass_i_values.index(conversion)
            for value in mass_i_conver[index:]:
                measure = measure / value

            return measure

        m_values = ['mm', 'cm', 'm', 'km']
        i_values = ["ml", "yd", "ft", "in"]
        i_conver = [1760, 3, 12]

        mass_m_values = ["mg", "g", "kg", "t"]
        mass_i_values = ["t", "lb", "oz"]
        mass_i_conver = [2204.62, 16]

        if symbol in m_values and conversion in i_values:
            measure = m_to_i(measure, symbol, conversion)
        elif symbol in i_values and conversion in m_values:
            measure = i_to_m(measure, symbol, conversion)
        elif symbol in mass_m_values and conversion in mass_i_values:
            measure = mass_m_to_i(measure, symbol, conversion)
        elif symbol in mass_i_values and conversion in mass_m_values:
            measure = mass_i_to_m(measure, symbol, conversion)
        elif symbol == 'c':
            measure = temp(c=measure)
        elif symbol == 'f':
            measure = temp(f=measure)
        else:
            msg = ":negative_squared_cross_mark: | Not a convertible symbol. \nImperial length unit symbols: {}\nImperial weight/mass unit symbols: {}\nMetric length unit symbols: {}\nMetric weight/mass unit symbols: {}\nTemperature unit symbols: c - f"
            await ctx.send(msg.format(" - ".join(i_values), " - ".join(mass_i_values), " - ".join(m_values), " - ".join(mass_m_values)))
            return

        await ctx.send(f":white_check_mark: | **{measure}{conversion}**")

def setup(bot):
    bot.add_cog(Utilities(bot))

