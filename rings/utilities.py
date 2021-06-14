import discord
from discord.ext import commands

from rings.utils.utils import react_menu, time_converter, BotError
from rings.utils.converters import MemberConverter
from rings.utils.checks import leaderboard_enabled, has_perms

import random
import aiohttp
import datetime
from simpleeval import simple_eval
from collections import defaultdict

class Utilities(commands.Cog):
    """A bunch of useful commands to do various tasks."""
    def __init__(self, bot):
        self.bot = bot
        
        def factory():
            return {"end": True, "list" : []}

        self.queue = defaultdict(factory)
        
    #######################################################################
    ## Commands
    #######################################################################

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
            raise BotError("Mathematical equation not recognized")
        except Exception as e:
            raise BotError(str(e))

    @commands.command()
    @commands.guild_only()
    async def serverinfo(self, ctx):
        """Returns a rich embed of the server's information. 
        
        {usage}"""
        guild = ctx.guild
        embed = discord.Embed(title=guild.name, colour=self.bot.bot_color, description="Info on this server")
        embed.set_thumbnail(url=guild.icon_url)
        embed.set_footer(**self.bot.bot_footer)

        embed.add_field(name="**Date Created**", value=guild.created_at.strftime("%d - %B - %Y %H:%M"))
        embed.add_field(name="**Owner**", value=str(guild.owner), inline=True)

        embed.add_field(name="**Members**", value=guild.member_count, inline=True)

        embed.add_field(name="**Region**", value=guild.region)
        embed.add_field(name="**Server ID**", value=guild.id, inline=True)

        channel_list = [channel.name for channel in guild.channels]
        channels = ", ".join(channel_list) if len(", ".join(channel_list)) < 1024 else ""
        role_list = [role.name for role in guild.roles]
        roles = ", ".join(role_list) if len(", ".join(role_list)) < 1024 else ""
        embed.add_field(name="**Channels**", value=f"{len(channel_list)}: {channels}", inline=False)
        embed.add_field(name="**Roles**", value=f"{len(role_list)}: {roles}", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def avatar(self, ctx,* , user : MemberConverter=None):
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
            url = f'https://history.muffinlabs.com/date{date}'
        else:
            url = 'https://history.muffinlabs.com/date'

        if choice:
            choice = choice.lower().title()
            if choice[-1] != "s":
                choice += "s"  
        else:
            choice = random.choice(["Deaths", "Births", "Events"])

        if not choice in ["Deaths", "Births", "Events"]:
            raise BotError("Not a correct choice. Correct choices are `Deaths`, `Births` or `Events`.")

        async with self.bot.session.get(url, headers={"Connection": "keep-alive"}) as r:
            try:
                res = await r.json()
            except aiohttp.ClientResponseError:
                res = await r.json(content_type="application/javascript")

        def _embed_generator(index, entries):
            page, max_page = index
            embed = discord.Embed(
                title=res['date'], 
                colour=self.bot.bot_color, 
                url=res["url"], 
                description=f"Necrobot is proud to present: **{choice} today in History**\n Page {page}/{max_page}"
            )
            
            embed.set_footer(**self.bot.bot_footer)
            
            for event in entries:
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

        await react_menu(ctx, res["data"][choice], 5, _embed_generator)

    @commands.group(invoke_without_command=True)
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
            raise BotError(" Something went wrong, you need to use the format: **<message> in <time>**")

        text, _, time = message.rpartition(" in ")
        sleep = time_converter(time)

        reminder_id = await self.bot.db.insert_reminder(ctx.author.id, ctx.channel.id, text, time, datetime.datetime.now())
        task = self.bot.loop.create_task(self.bot.meta.reminder_task(reminder_id, sleep, text, ctx.channel.id, ctx.author.id))
        self.bot.reminders[reminder_id] = task

        await ctx.send(f":white_check_mark: | I will remind you of that in **{time}**")

    @remindme.command(name="delete")
    async def remindme_delete(self, ctx, reminder_id : int):
        """Cancels a reminder based on its id on the reminder list. You can check out the id of each
        reminder using `remindme list`.

        {usage}

        __Examples__
        `{pre}remindme delete 545454` - delete the reminder with id 545454
        `{pre}remindme delete 143567` - delete the reminder with id 143567
        """
        
        exists = await self.bot.db.delete_reminder(reminder_id)
        if not exists:
            raise BotError("No reminder with that ID could be found.")
        
        self.bot.reminders[reminder_id].cancel()
        del self.bot.reminders[reminder_id]
        await ctx.send(":white_check_mark: | Reminder cancelled")

    @remindme.command(name="list")
    async def remindme_list(self, ctx, user : MemberConverter = None):
        """List all the reminder you currently have in necrobot's typical paginator. All the reminders include their
        position on the remindme list which can be given to `remindme delete` to cancel a reminder.

        {usage}

        __Exampes__
        `{pre}remindme list` - lists all of your reminders
        `{pre}remindme list @NecroBot` - list all of NecroBot's reminder
        """
        def embed_generator(index, entries):
            embed = discord.Embed(
                title=f"Reminders ({index[0]}/{index[1]})", 
                description=f"Here is the list of **{user.display_name}**'s currently active reminders.", 
                colour=self.bot.bot_color
            )
            
            embed.set_footer(**self.bot.bot_footer)
            
            for reminder in entries:
                embed.add_field(
                    name=f'{reminder["id"]}: {reminder["timer"]}', 
                    value=reminder["reminder"][:500], 
                    inline=False
                )

            return embed

        if not user:
            user = ctx.author
            
        reminders = await self.bot.db.get_reminders(user.id)
        await react_menu(ctx, reminders, 10, embed_generator)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def q(self, ctx):
        """Displays the content of the queue at the moment. Queue are shortlive instances, do not use them to
        hold data for extended periods of time. A queue should atmost only last a couple of days.

        {usage}"""
        def embed_maker(index, entries):
            embed = discord.Embed(
                title=f"Queue ({index[0]}/{index[1]})", 
                description="Here is the list of members currently queued:\n- {}".format('\n- '.join(entries)), 
                colour=self.bot.bot_color
            )
            
            embed.set_footer(**self.bot.bot_footer)
            
            return embed
            
        queue = [f"**{ctx.guild.get_member(x).display_name}**" for x in self.queue[ctx.guild.id]["list"]]
        await react_menu(ctx, queue, 10, embed_maker)


    @q.command(name="start")
    @commands.guild_only()
    @has_perms(2)
    async def q_start(self, ctx):
        """Starts a queue, if there is already an ongoing queue it will fail. The ongoing queue must be cleared first 
        using `{pre}q clear`.

        {usage}"""
        if self.queue[ctx.guild.id]["list"]:
            raise BotError("A queue is already ongoing, please clear the queue first")

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
            raise BotError(" Sorry, you can no longer add yourself to the queue")

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
        if not self.queue[ctx.guild.id]["list"]:
            raise BotError(" No users left in that queue")

        msg = f":bell: | {ctx.guild.get_member(self.queue[ctx.guild.id]['list'][0]).mention}, you're next. Get ready!"

        if len(self.queue[ctx.guild.id]["list"]) > 1:
            msg += f" \n{ctx.guild.get_member(self.queue[ctx.guild.id]['list'][1]).mention}, you're right after them. Start warming up!"
        else:
            msg += "\nThat's the last user in the queue"

        await ctx.send(msg)
        self.queue[ctx.guild.id]["list"].pop(0)
        
    @commands.group(invoke_without_command=True)
    @leaderboard_enabled()
    async def leaderboard(self, ctx, page : int = 0):
        """Base command for the leaderboard, a fun system built for servers to be able to have their own arbitrary 
        point system.
        
        {usage}
        
        __Examples__
        `{pre}leaderboard` - show the leaderboard starting from page zero
        `{pre}leaderboard 3` - show the leaderboard starting from page 3
        """   
        message, symbol = await self.bot.db.get_leaderboard(ctx.guild.id)
                
        results = await self.bot.db.query(
            "SELECT * FROM necrobot.LeaderboardPoints WHERE guild_id=$1 ORDER BY points DESC",
            ctx.guild.id
        )
        
        def _embed_maker(index, entries):
            users = []
            for result in entries:
                user = ctx.guild.get_member(result[0])
                if user is not None:
                    users.append(f"- {user.mention}: {result[2]} {symbol}")
            
            users = "\n\n".join(users)
            msg = f"{message}\n\n{users}"
            embed = discord.Embed(
                title=f"Leaderboard ({index[0]}/{index[1]})", 
                colour=self.bot.bot_color, 
                description=msg
            )
            
            embed.set_footer(**self.bot.bot_footer)

            return embed
                        
        await react_menu(ctx, results, 10, _embed_maker, page=page)
        
    @leaderboard.command(name="message")
    @has_perms(4)
    async def leaderboard_message(self, ctx, *, message : str = ""):
        """Enable the leaderboard and set a message. (Permission level of 4+)
        
        {usage}
        
        __Examples__
        `{pre}leaderboard message` - disable leaderboards
        `{pre}leaderboard message Server's Favorite People` - enable leaderboards and make 
        """
        if message == "":
            await ctx.send(":white_check_mark: | Leaderboard disabled")
        elif len(message) > 200:
            raise BotError(" The message cannot be more than 200 characters")
        else:
            await ctx.send(":white_check_mark: | Leaderboard message changed")
            
        await self.bot.db.update_leaderboard(ctx.guild.id, message=message)
        
    @leaderboard.command(name="symbol")
    @has_perms(4)
    @leaderboard_enabled()
    async def leaderboard_symbol(self, ctx, *, symbol):
        """Change the symbol for your points (Permission level of 4+)
        
        {usage}
        
        __Examples__
        `{pre}leaderboard symbol $` - make the symbol $
        """        
        if len(symbol) > 50:
            raise BotError(" The symbol cannot be more than 50 characters")
        
        await ctx.send(":white_check_mark: | Leaderboard symbol changed")    
        await self.bot.db.update_leaderboard(ctx.guild.id, symbol=symbol)
    
    @leaderboard.command(name="award")
    @has_perms(2)
    @leaderboard_enabled()
    async def leaderboard_award(self, ctx, user : MemberConverter, points : int):
        """Add remove some points. (Permission level of 2+)
        
        {usage}
        
        __Examples__
        `{pre}leaderboard award 340` - award 340 points
        `{pre}leaderboard award -34` - award -34 points, effectively removing 34 points.
        """
        _, symbol = await self.bot.db.get_leaderboard(ctx.guild.id)
        
        await self.bot.db.update_leaderboard_member(ctx.guild.id, user.id, points)
        if points > 0:
            await ctx.send(f"{user.mention}, you have been awarded {points} {symbol}")
        else:
            await ctx.send(f"{user.mention}, {points} {symbol} has been taken from you")
    
def setup(bot):
    bot.add_cog(Utilities(bot))
