from __future__ import annotations

import asyncio
import datetime
import random
from typing import TYPE_CHECKING, Annotated, Any, Dict, List, Literal

import aiohttp
import discord
from discord.ext import commands
from simpleeval import simple_eval

from rings.utils.astral import Astral
from rings.utils.checks import has_perms, leaderboard_enabled
from rings.utils.converters import MemberConverter
from rings.utils.ui import Paginator
from rings.utils.utils import BotError, format_dt, time_converter, time_string_parser

if TYPE_CHECKING:
    from bot import NecroBot


class Utilities(commands.Cog):
    """A bunch of useful commands to do various tasks."""

    def __init__(self, bot: NecroBot):
        self.bot = bot
        self.shortcut_mapping = ["Y", "X", "C", "V", "B"]

    #######################################################################
    ## Commands
    #######################################################################

    @commands.command()
    async def calc(self, ctx: commands.Context[NecroBot], *, equation: str):
        """Evaluates a pythonic mathematical equation, use the following to build your mathematical equations:
        `*` - for multiplication
        `+` - for additions
        `-` - for subtractions
        `/` - for divisions
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
        except NameError as e:
            raise BotError("Mathematical equation not recognized") from e
        except Exception as e:
            raise BotError(str(e)) from e

    @commands.command()
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context[NecroBot]):
        """Returns a rich embed of the server's information.

        {usage}"""
        guild = ctx.guild
        embed = discord.Embed(
            title=guild.name,
            colour=self.bot.bot_color,
            description="Info on this server",
        )
        embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(**self.bot.bot_footer)

        embed.add_field(
            name="**Date Created**",
            value=guild.created_at.strftime("%d - %B - %Y %H:%M"),
        )
        embed.add_field(name="**Owner**", value=str(guild.owner), inline=True)

        embed.add_field(name="**Members**", value=guild.member_count, inline=True)

        embed.add_field(name="**Server ID**", value=guild.id, inline=True)

        channel_list = [channel.name for channel in guild.channels]
        channels = ", ".join(channel_list) if len(", ".join(channel_list)) < 1024 else ""
        role_list = [role.name for role in guild.roles]
        roles = ", ".join(role_list) if len(", ".join(role_list)) < 1024 else ""
        embed.add_field(name="**Channels**", value=f"{len(channel_list)}: {channels}", inline=False)
        embed.add_field(name="**Roles**", value=f"{len(role_list)}: {roles}", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def avatar(
        self,
        ctx: commands.Context[NecroBot],
        *,
        user: Annotated[discord.Member, MemberConverter] = commands.Author,
    ):
        """Returns a link to the given user's profile pic

        {usage}

        __Example__
        `{pre}avatar @NecroBot` - return the link to NecroBot's avatar"""
        avatar = user.display_avatar.replace(format="png")
        await ctx.send(embed=discord.Embed().set_image(url=avatar))

    @commands.command()
    async def today(
        self,
        ctx: commands.Context[NecroBot],
        choice: Literal["events", "deaths", "births"] = None,
        date: str = None,
    ):
        """Creates a rich information about events/deaths/births that happened today or any day you indicate using the \
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

        def embed_maker(view: Paginator, entries: List[Dict[str, Any]]):
            embed = discord.Embed(
                title=res["date"],
                colour=self.bot.bot_color,
                url=res["url"],
                description=f"Necrobot is proud to present: **{choice} today in History**\n Page {view.page_string}",
            )

            embed.set_footer(**self.bot.bot_footer)

            for event in entries:
                try:
                    if choice == "Events":
                        link_list = "".join([f"\n-[{x['title']}]({x['link']})" for x in event["links"]])
                        embed.add_field(
                            name=f"Year {event['year']}",
                            value=f"{event['text']}\n__Links__{link_list}",
                            inline=False,
                        )
                    elif choice == "Deaths":
                        embed.add_field(
                            name=f"Year {event['year']}",
                            value=f"[{event['text'].replace('b.','Birth: ')}]({event['links'][0]['link']})",
                            inline=False,
                        )
                    elif choice == "Births":
                        embed.add_field(
                            name=f"Year {event['year']}",
                            value=f"[{event['text'].replace('d.','Death: ')}]({event['links'][0]['link']})",
                            inline=False,
                        )
                except AttributeError:
                    pass

            return embed

        if date:
            r_date = date.split("/")
            date = f"/{r_date[1]}/{r_date[0]}"
            url = f"https://history.muffinlabs.com/date{date}"
        else:
            url = "https://history.muffinlabs.com/date"

        if choice:
            choice = choice.lower().title()
            if choice[-1] != "s":
                choice += "s"
        else:
            choice = random.choice(["Deaths", "Births", "Events"])

        if choice not in ["Deaths", "Births", "Events"]:
            raise BotError("Not a correct choice. Correct choices are `Deaths`, `Births` or `Events`.")

        async with ctx.typing():
            async with self.bot.session.get(url, headers={"Connection": "keep-alive"}) as r:
                try:
                    res = await r.json()
                except aiohttp.ClientResponseError:
                    res = await r.json(content_type="application/javascript")

        await Paginator(5, res["data"][choice], ctx.author, embed_maker=embed_maker).start(ctx)

    @commands.group(invoke_without_command=True)
    async def remindme(self, ctx: commands.Context[NecroBot], *, message):
        """Creates a reminder in seconds. The following times can be used: days (d), \
        hours (h), minutes (m), seconds (s). You can also pass a timestamp to be reminded \
        at a certain date in the format "YYYY/MM/DD HH:MM". You can omit either sides if you \
        want to be reminded only on a specific date or only at a specific hour

        {usage}

        __Examples__
        `{pre}remindme do the dishes in 40seconds` - will remind you to do the dishes in 40 seconds
        `{pre}remindme do the dishes in 2m` - will remind you to do the dishes in 2 minutes
        `{pre}remindme do the dishes in 4day 2h45minutes` - will remind you to do the dishes in 4 days, 2 hours and 45 minutes
        `{pre}remindme in 2 hours` - send you a ping in 2 hours
        `{pre}remindme on 17:22` - get reminded at a specific hour today
        `{pre}remindme on 2023/04/22` - get reminded at a specific date
        `{pre}remindme on 2023/04/22 17:22` - get reminded at a specific date and hour
        """
        try:
            text, sleep, time = time_string_parser(message)
        except Exception as e:
            raise BotError(str(e))

        if sleep < 1:
            raise BotError("Can't have a reminder that's less than one second!")

        reminder_id = await self.bot.db.insert_reminder(
            ctx.author.id,
            ctx.channel.id,
            text,
            time,
            datetime.datetime.now(datetime.timezone.utc),
        )
        task = self.bot.loop.create_task(
            self.bot.meta.reminder_task(reminder_id, sleep, text, ctx.channel.id, ctx.author.id)
        )
        self.bot.reminders[reminder_id] = task

        stamp = format_dt(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=sleep),
            style="f",
        )
        await ctx.send(f":white_check_mark: | I will remind you of that on **{stamp}** (ID: {reminder_id})")

    @remindme.command(name="delete")
    async def remindme_delete(self, ctx: commands.Context[NecroBot], reminder_id: int):
        """Cancels a reminder based on its id on the reminder list. You can check out the id of each \
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
    async def remindme_list(self, ctx: commands.Context[NecroBot]):
        """List all the reminder you currently have in necrobot's typical paginator. All the reminders include their \
        position on the remindme list which can be given to `remindme delete` to cancel a reminder.

        {usage}

        __Exampes__
        `{pre}remindme list` - lists all of your reminders
        """
        user = ctx.author

        def embed_maker(view: Paginator, entries: List[Dict[str, Any]]):
            embed = discord.Embed(
                title=f"Reminders ({view.page_string})",
                description=f"Here is the list of **{user.display_name}**'s currently active reminders.",
                colour=self.bot.bot_color,
            )

            embed.set_footer(**self.bot.bot_footer)

            for reminder in entries:
                stamp = format_dt(
                    reminder["start_date"] + datetime.timedelta(seconds=time_converter(reminder["timer"])),
                    style="f",
                )
                text = reminder["reminder"][:500] if reminder["reminder"][:500] else "`No Text`"
                embed.add_field(name=f'{reminder["id"]}: {stamp}', value=text, inline=False)

            return embed

        reminders = await self.bot.db.get_reminders(user.id)
        await Paginator(10, reminders, ctx.author, embed_maker=embed_maker).start(ctx)

    @commands.group(invoke_without_command=True, aliases=["queue"])
    @commands.guild_only()
    async def q(self, ctx: commands.Context[NecroBot]):
        """Displays the content of the queue at the moment. Queue are shortlived instances, do not use them to \
        hold data for extended periods of time. A queue should at most only last a couple of days.

        {usage}"""

        def embed_maker(view: Paginator, entries: List[Dict[str, Any]]):
            description = "\n".join(entries)
            embed = discord.Embed(
                title=f"Queue ({view.page_string})",
                description=f"Here is the list of members currently queued:\n{description}",
                colour=self.bot.bot_color,
            )

            embed.set_footer(**self.bot.bot_footer)

            return embed

        queue = [
            f"**{index+1}.** {ctx.guild.get_member(x).display_name}"
            for index, x in enumerate(self.bot.queue[ctx.guild.id]["list"])
        ]
        await Paginator(15, queue, ctx.author, embed_maker=embed_maker).start(ctx)

    @q.command(name="start")
    @has_perms(2)
    async def q_start(self, ctx: commands.Context[NecroBot]):
        """Starts a queue, if there is already an existing queue this will resume it. The ongoing queue must \
        be cleared first using `{pre}q clear`.

        {usage}"""
        if not self.bot.queue[ctx.guild.id]["end"]:
            raise BotError("Current queue has not ended, end the queue first.")

        self.bot.queue[ctx.guild.id]["end"] = False

        if self.bot.queue[ctx.guild.id]["list"]:
            await ctx.send(":white_check_mark: | Exising queue resumed")
        else:
            await ctx.send(":white_check_mark: | New queue started")

    @q.command(name="end")
    @has_perms(2)
    async def q_end(self, ctx: commands.Context[NecroBot]):
        """Ends a queue but does not clear it. Users will no longer be able to use `{pre}q me` \
        but you can still resume the same queue and keep going through it.

        {usage}"""
        self.bot.queue[ctx.guild.id]["end"] = True
        await ctx.send(":white_check_mark: | Users will now be unable to add themselves to queue")

    @q.command(name="clear")
    @has_perms(2)
    async def q_clear(self, ctx: commands.Context[NecroBot]):
        """Ends a queue and clears it. Users will no longer be able to add themselves and the content of the queue will be \
        emptied. Use it in order to start a new queue.

        {usage}"""
        self.bot.queue[ctx.guild.id] = self.bot.queue.default_factory()
        await ctx.send(
            ":white_check_mark: | Queue cleared and ended. Please start a new queue to be able to add users again"
        )

    @q.command(name="me")
    @commands.guild_only()
    async def q_me(self, ctx: commands.Context[NecroBot]):
        """Queue the user that used the command to the current queue. Will fail if queue has been ended. \
        :warning: **If the user is already in the queue it will remove them, check whether you are in the \
        queue first** :warning: 

        {usage}"""
        if self.bot.queue[ctx.guild.id]["end"]:
            raise BotError("Sorry, you can no longer add yourself to the queue")

        if ctx.author.id in self.bot.queue[ctx.guild.id]["list"]:
            await ctx.send(":white_check_mark: | You have been removed from the queue")
            self.bot.queue[ctx.guild.id]["list"].remove(ctx.author.id)
            return

        self.bot.queue[ctx.guild.id]["list"].append(ctx.author.id)
        position = len(self.bot.queue[ctx.guild.id]["list"])
        await ctx.send(f":white_check_mark: |  You have been added to the queue at position **{position}**")

    @q.command(name="next")
    @has_perms(2)
    async def q_next(self, ctx: commands.Context[NecroBot]):
        """Mentions the next user and the one after that so they can get ready.

        {usage}"""
        if not self.bot.queue[ctx.guild.id]["list"]:
            raise BotError("No users left in that queue")

        msg = f":bell: | {ctx.guild.get_member(self.bot.queue[ctx.guild.id]['list'][0]).mention}, you're next. Get ready!"

        if len(self.bot.queue[ctx.guild.id]["list"]) > 1:
            msg += f" \n{ctx.guild.get_member(self.bot.queue[ctx.guild.id]['list'][1]).mention}, you're right after them. Start warming up!"
        else:
            msg += "\nThat's the last user in the queue"

        await ctx.send(msg)
        self.bot.queue[ctx.guild.id]["list"].pop(0)

    @q.command(name="edit")
    @has_perms(2)
    async def q_edit(
        self,
        ctx: commands.Context[NecroBot],
        member: Annotated[discord.Member, MemberConverter],
        position: int = None,
    ):
        """Remove or add a user in a queue. If the user is in the queue this will remove then. \
        If they are not, this will add them. You can add a user at a specific spot in the \
        queue with the position argument.
        
        {usage}
        
        __Examples__
        `{pre}q edit @Necro` - given Necro is in the queue, this will remove them from the queue
        `{pre}q edit @Necro` - given Necro is not in the queue, this will add then to the last spot
        `{pre}q edit @Necro 1` - this will move or add Necro to the first position in the queue
        `{pre}q edit @Necro 5` - this will move or add Necro to the fifth position in the queue
        """
        max_len = len(self.bot.queue[ctx.guild.id]["list"]) + 1
        new_position = max_len
        if position is not None:
            new_position = position

        if 1 > new_position > max_len:
            raise BotError(f"New position must be between 1 and {max_len}")

        if member.id in self.bot.queue[ctx.guild.id]["list"]:
            self.bot.queue[ctx.guild.id]["list"].remove(member.id)

            if position is None:
                return await ctx.send(
                    f":white_check_mark: | **{member.display_name}** has been removed from the queue"
                )

        self.bot.queue[ctx.guild.id]["list"].insert(new_position - 1, member.id)
        await ctx.send(
            f":white_check_mark: | **{member.display_name}** has been inserted into position **{new_position}**"
        )

    @commands.group(invoke_without_command=True)
    @leaderboard_enabled()
    async def leaderboard(self, ctx: commands.Context[NecroBot]):
        """Base command for the leaderboard, a fun system built for servers to be able to have their own arbitrary \
        point system.

        {usage}

        __Examples__
        `{pre}leaderboard` - show the leaderboard starting from page zero
        """
        message, symbol = await self.bot.db.get_leaderboard(ctx.guild.id)

        results = await self.bot.db.query(
            "SELECT * FROM necrobot.LeaderboardPoints WHERE guild_id=$1 ORDER BY points DESC",
            ctx.guild.id,
        )

        def embed_maker(view: Paginator, entries: List[Dict[str, Any]]):
            users = []
            for result in entries:
                user = ctx.guild.get_member(result[0])
                if user is not None:
                    users.append(f"- {user.mention}: {result[2]} {symbol}")

            users = "\n\n".join(users)
            msg = f"{message}\n\n{users}"
            embed = discord.Embed(
                title=f"Leaderboard ({view.page_string})",
                colour=self.bot.bot_color,
                description=msg,
            )

            embed.set_footer(**self.bot.bot_footer)

            return embed

        await Paginator(10, results, ctx.author, embed_maker=embed_maker).start(ctx)

    @leaderboard.command(name="message")
    @has_perms(4)
    async def leaderboard_message(self, ctx: commands.Context[NecroBot], *, message: str = ""):
        """Enable the leaderboard and set a message.

        {usage}

        __Examples__
        `{pre}leaderboard message` - disable leaderboards
        `{pre}leaderboard message Server's Favorite People` - enable leaderboards and make
        """
        if message == "":
            await ctx.send(":white_check_mark: | Leaderboard disabled")
        elif len(message) > 200:
            raise BotError("The message cannot be more than 200 characters")
        else:
            await ctx.send(":white_check_mark: | Leaderboard message changed")

        await self.bot.db.update_leaderboard(ctx.guild.id, message=message)

    @leaderboard.command(name="symbol")
    @has_perms(4)
    @leaderboard_enabled()
    async def leaderboard_symbol(self, ctx: commands.Context[NecroBot], *, symbol):
        """Change the symbol for your points

        {usage}

        __Examples__
        `{pre}leaderboard symbol $` - make the symbol $
        """
        if len(symbol) > 50:
            raise BotError("The symbol cannot be more than 50 characters")

        await ctx.send(":white_check_mark: | Leaderboard symbol changed")
        await self.bot.db.update_leaderboard(ctx.guild.id, symbol=symbol)

    @leaderboard.command(name="award")
    @has_perms(2)
    @leaderboard_enabled()
    async def leaderboard_award(
        self,
        ctx: commands.Context[NecroBot],
        user: Annotated[discord.Member, MemberConverter],
        points: int,
    ):
        """Add remove some points.
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

    @commands.command()
    async def sun(self, ctx: commands.Context[NecroBot], city: str, date: str = None):
        """Get the sunrise and sunset for today based on a city, with an \
        optional date in DD/MM/YYYY

        {usage}

        __Examples__
        `{pre}sun London` - get sunrise and sunset for today for London
        `{pre}sun London 22/04/2019` - get sunrise and sunset for the 22 of april 2019 in London
        """

        def to_string(dt):
            return dt.strftime("%H:%M")

        def suffix(d):
            return "th" if 11 <= d <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th")

        def custom_strftime(dt_format, t):
            return t.strftime(dt_format).replace("{S}", str(t.day) + suffix(t.day))

        a = Astral()
        try:
            location = a[city]
        except KeyError as e:
            raise BotError(f"City **{city}** not found in possible cities") from e

        if date is not None:
            try:
                date = datetime.datetime.strptime(date, "%d/%m/%Y")
            except ValueError as e:
                raise BotError("Date not in DD/MM/YYYY format or not valid") from e
        else:
            date = datetime.datetime.now(datetime.timezone.utc)

        sun = location.sun(date)

        date_string = custom_strftime("%A {S} %B, %Y", date)
        description = f"**Sunrise**: {to_string(sun['sunrise'])} \n**Sunset**: {to_string(sun['sunset'])}"
        embed = discord.Embed(colour=self.bot.bot_color, title=date_string, description=description)
        embed.set_footer(**self.bot.bot_footer)

        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def giveaway(self, ctx: commands.Context[NecroBot], winners: int, *, time_string: str):
        """Start a giveaway that will last for the specified time, after that time a number of winners specified \
        with the [winners] argument will be selected. The following times can be used: days (d), \
        hours (h), minutes (m), seconds (s).

        {usage}

        __Examples__
        `{pre}giveaway 3 A hug in 3d` - start a giveaway that will last three days and have three winners
        """
        text, sleep, _ = time_string_parser(time_string)
        if sleep < 1:
            raise BotError("Can't have a giveaway that's less than a second!")

        embed = discord.Embed(
            colour=self.bot.bot_color,
            title="Giveaway!",
            description=f"{ctx.author.mention} is doing a giveaway! The reward is: \n\n {text} \n\n **React with :gift: to enter!**",
        )
        embed.add_field(name="# of Winners", value=winners)

        limit = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=sleep)
        embed.add_field(name="Duration", value=format_dt(limit, style="f"))

        embed.set_footer(**self.bot.bot_footer)

        msg = await ctx.send(embed=embed)
        await msg.add_reaction("\N{WRAPPED PRESENT}")
        self.bot.ongoing_giveaways[msg.id] = {
            "limit": limit,
            "winners": winners,
            "reward": text,
            "msg": msg,
            "entries": [],
        }

        # The Long Nap
        await asyncio.sleep(sleep)
        ga_results = self.bot.ongoing_giveaways.pop(msg.id, None)

        if ga_results is None:
            return

        await msg.edit(content=":white_check_mark: The giveaway has ended!", embed=embed)

        winner_users = []
        for entry in ga_results["entries"]:
            user = ctx.guild.get_member(entry)
            if user is None or user.bot:
                continue

            winner_users.append(user.mention)

        if not winner_users:
            return await msg.reply("No valid entries for giveaway")

        if len(winner_users) <= winners:
            winner_mentions = winner_users
        else:
            winner_mentions = random.sample(winner_users, winners)

        embed = discord.Embed(
            colour=self.bot.bot_color,
            title="Giveaway Result",
            description=f"The giveaway by {ctx.author.mention} has ended! The reward is: \n\n {text}",
        )
        embed.add_field(name="Giveaway Link", value=f"[Link]({msg.jump_url})")
        embed.set_footer(**self.bot.bot_footer)
        await msg.reply(
            f"Giveaway Ended! Congratulations to {', '.join(winner_mentions)}",
            embed=embed,
        )

    @giveaway.command(name="list")
    @commands.guild_only()
    async def giveaway_list(self, ctx: commands.Context[NecroBot]):
        """Get a list of all current giveaways in this server

        {usage}"""
        ga_entries = [x for x in self.bot.ongoing_giveaways.values() if x["msg"].guild.id == ctx.guild.id]
        ga_entries.sort(key=lambda x: x["limit"])

        def embed_maker(view: Paginator, entries: List[Dict[str, Any]]):
            ga = "\n".join(
                [
                    f"- **{entry['msg'].id}**: {format_dt(entry['limit'])} ([Link]({entry['msg'].jump_url}))"
                    for entry in entries
                ]
            )
            embed = discord.Embed(
                title=f"Giveaways ({view.page_string})",
                colour=self.bot.bot_color,
                description=ga,
            )

            embed.set_footer(**self.bot.bot_footer)

            return embed

        await Paginator(10, ga_entries, ctx.author, embed_maker=embed_maker).start(ctx)

    @giveaway.command(name="cancel")
    @commands.guild_only()
    async def giveaway_cancel(self, ctx: commands.Context[NecroBot], msg_id: int):
        """Cancel an ongoing giveaway, see `giveaway list` for a list of giveaways and their ID's

        {usage}

        __Example__
        `{pre}giveaway cancel 2` - cancel giveaway 2
        """
        if msg_id not in self.bot.ongoing_giveaways:
            raise BotError("No giveaway with that ID found.")

        ga = self.bot.ongoing_giveaways.pop(msg_id)["msg"]

        perms = await ctx.bot.db.get_permission(ctx.message.author.id, ctx.guild.id)
        level = 3
        if perms < level and not ga.author.id == ctx.author.id:
            raise commands.CheckFailure(
                f"You do not have the required NecroBot permissions. Your permission level must be {level} or you must be the author of the giveaway."
            )

        await ctx.send(f":white_check_mark: | Giveaway cancelled. {ga.jump_url}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.message_id not in self.bot.ongoing_giveaways:
            return

        if (
            datetime.datetime.now(datetime.timezone.utc)
            > self.bot.ongoing_giveaways[payload.message_id]["limit"]
        ):
            return

        if payload.emoji.name == "\N{WRAPPED PRESENT}":
            self.bot.ongoing_giveaways[payload.message_id]["entries"].append(payload.user_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.message_id not in self.bot.ongoing_giveaways:
            return

        if (
            datetime.datetime.now(datetime.timezone.utc)
            > self.bot.ongoing_giveaways[payload.message_id]["limit"]
        ):
            return

        if (
            payload.emoji.name == "\N{WRAPPED PRESENT}"
            and payload.user_id in self.bot.ongoing_giveaways[payload.message_id]["entries"]
        ):
            self.bot.ongoing_giveaways[payload.message_id]["entries"].remove(payload.user_id)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.message_id in self.bot.ongoing_giveaways:
            del self.bot.ongoing_giveaways[payload.message_id]


async def setup(bot: NecroBot):
    await bot.add_cog(Utilities(bot))
