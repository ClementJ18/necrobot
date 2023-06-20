import asyncio
import datetime
import io
import random
from collections import defaultdict

import aiohttp
import discord
from discord.ext import commands
from simpleeval import simple_eval

from rings.utils.astral import Astral
from rings.utils.BIG import pack_file
from rings.utils.checks import has_perms, leaderboard_enabled
from rings.utils.converters import MemberConverter
from rings.utils.ui import paginate
from rings.utils.utils import (BotError, format_dt, time_converter,
                               time_string_parser)


class Utilities(commands.Cog):
    """A bunch of useful commands to do various tasks."""

    def __init__(self, bot):
        self.bot = bot
        self.shortcut_mapping = ["Y", "X", "C", "V", "B"]

        def factory():
            return {"end": True, "list": []}

        self.queue = defaultdict(factory)

    #######################################################################
    ## Commands
    #######################################################################

    @commands.command()
    async def calc(self, ctx: commands.Context, *, equation: str):
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
        except NameError as e:
            raise BotError("Mathematical equation not recognized") from e
        except Exception as e:
            raise BotError(str(e)) from e

    @commands.command()
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context):
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
        embed.add_field(
            name="**Channels**", value=f"{len(channel_list)}: {channels}", inline=False
        )
        embed.add_field(name="**Roles**", value=f"{len(role_list)}: {roles}", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def avatar(self, ctx: commands.Context, *, user: MemberConverter = None):
        """Returns a link to the given user's profile pic

        {usage}

        __Example__
        `{pre}avatar @NecroBot` - return the link to NecroBot's avatar"""
        if user is None:
            user = ctx.author

        avatar = user.display_avatar.replace(format="png")
        await ctx.send(embed=discord.Embed().set_image(url=avatar))

    @commands.command()
    async def today(self, ctx: commands.Context, choice: str = None, date: str = None):
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
            raise BotError(
                "Not a correct choice. Correct choices are `Deaths`, `Births` or `Events`."
            )

        async with self.bot.session.get(url, headers={"Connection": "keep-alive"}) as r:
            try:
                res = await r.json()
            except aiohttp.ClientResponseError:
                res = await r.json(content_type="application/javascript")

        def embed_maker(view, entries):
            embed = discord.Embed(
                title=res["date"],
                colour=self.bot.bot_color,
                url=res["url"],
                description=f"Necrobot is proud to present: **{choice} today in History**\n Page {view.page_number}/{view.page_count}",
            )

            embed.set_footer(**self.bot.bot_footer)

            for event in entries:
                try:
                    if choice == "Events":
                        link_list = "".join(
                            [f"\n-[{x['title']}]({x['link']})" for x in event["links"]]
                        )
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

        await paginate(ctx, res["data"][choice], 5, embed_maker)

    @commands.group(invoke_without_command=True)
    async def remindme(self, ctx: commands.Context, *, message):
        """Creates a reminder in seconds. The following times can be used: days (d),
        hours (h), minutes (m), seconds (s). You can also pass a timestamp to be reminded
        at a certain date in the format "YYYY/MM/DD HH:MM". You can omit either sides if you
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
        await ctx.send(f":white_check_mark: | I will remind you of that on **{stamp}**")

    @remindme.command(name="delete")
    async def remindme_delete(self, ctx: commands.Context, reminder_id: int):
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
    async def remindme_list(self, ctx: commands.Context, user: MemberConverter = None):
        """List all the reminder you currently have in necrobot's typical paginator. All the reminders include their
        position on the remindme list which can be given to `remindme delete` to cancel a reminder.

        {usage}

        __Exampes__
        `{pre}remindme list` - lists all of your reminders
        `{pre}remindme list @NecroBot` - list all of NecroBot's reminder
        """

        def embed_maker(view, entries):
            embed = discord.Embed(
                title=f"Reminders ({view.page_number}/{view.page_count})",
                description=f"Here is the list of **{user.display_name}**'s currently active reminders.",
                colour=self.bot.bot_color,
            )

            embed.set_footer(**self.bot.bot_footer)

            for reminder in entries:
                stamp = format_dt(
                    reminder["start_date"]
                    + datetime.timedelta(seconds=time_converter(reminder["timer"])),
                    style="f",
                )
                text = reminder["reminder"][:500] if reminder["reminder"][:500] else "`No Text`"
                embed.add_field(name=f'{reminder["id"]}: {stamp}', value=text, inline=False)

            return embed

        if not user:
            user = ctx.author

        reminders = await self.bot.db.get_reminders(user.id)
        await paginate(ctx, reminders, 10, embed_maker)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def q(self, ctx: commands.Context):
        """Displays the content of the queue at the moment. Queue are shortlive instances, do not use them to
        hold data for extended periods of time. A queue should atmost only last a couple of days.

        {usage}"""

        def embed_maker(view, entries):
            embed = discord.Embed(
                title=f"Queue ({view.page_number}/{view.page_count})",
                description="Here is the list of members currently queued:\n- {}".format(
                    "\n- ".join(entries)
                ),
                colour=self.bot.bot_color,
            )

            embed.set_footer(**self.bot.bot_footer)

            return embed

        queue = [
            f"**{ctx.guild.get_member(x).display_name}**" for x in self.queue[ctx.guild.id]["list"]
        ]
        await paginate(ctx, queue, 10, embed_maker)

    @q.command(name="start")
    @commands.guild_only()
    @has_perms(2)
    async def q_start(self, ctx: commands.Context):
        """Starts a queue, if there is already an ongoing queue it will fail. The ongoing queue must be cleared first
        using `{pre}q clear`.

        {usage}"""
        if self.queue[ctx.guild.id]["list"]:
            raise BotError("A queue is already ongoing, please clear the queue first")

        self.queue[ctx.guild.id] = {"end": False, "list": []}
        await ctx.send(":white_check_mark: | Queue initialized")

    @q.command(name="end")
    @commands.guild_only()
    @has_perms(2)
    async def q_end(self, ctx: commands.Context):
        """Ends a queue but does not clear it. Users will no longer be able to use `{pre}q me`

        {usage}"""
        self.queue[ctx.guild.id]["end"] = True
        await ctx.send(
            ":white_check_mark: | Users will now not be able to add themselves to queue"
        )

    @q.command(name="clear")
    @commands.guild_only()
    @has_perms(2)
    async def q_clear(self, ctx: commands.Context):
        """Ends a queue and clears it. Users will no longer be able to add themselves and the content of the queue will be
        emptied. Use it in order to start a new queue

        {usage}"""
        self.queue[ctx.guild.id]["list"] = []
        self.queue[ctx.guild.id]["end"] = True
        await ctx.send(
            ":white_check_mark: | Queue cleared and ended. Please start a new queue to be able to add users again"
        )

    @q.command(name="me")
    @commands.guild_only()
    async def q_me(self, ctx: commands.Context):
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
    async def q_next(self, ctx: commands.Context):
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
    async def leaderboard(self, ctx: commands.Context):
        """Base command for the leaderboard, a fun system built for servers to be able to have their own arbitrary
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

        def embed_maker(view, entries):
            users = []
            for result in entries:
                user = ctx.guild.get_member(result[0])
                if user is not None:
                    users.append(f"- {user.mention}: {result[2]} {symbol}")

            users = "\n\n".join(users)
            msg = f"{message}\n\n{users}"
            embed = discord.Embed(
                title=f"Leaderboard ({view.page_number}/{view.page_count})",
                colour=self.bot.bot_color,
                description=msg,
            )

            embed.set_footer(**self.bot.bot_footer)

            return embed

        await paginate(ctx, results, 10, embed_maker)

    @leaderboard.command(name="message")
    @has_perms(4)
    async def leaderboard_message(self, ctx: commands.Context, *, message: str = ""):
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
    async def leaderboard_symbol(self, ctx: commands.Context, *, symbol):
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
    async def leaderboard_award(self, ctx: commands.Context, user: MemberConverter, points: int):
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

    @commands.command()
    async def sun(self, ctx: commands.Context, city: str, date: str = None):
        """Get the sunrise and sunset for today based on a city, with an
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
        description = (
            f"**Sunrise**: {to_string(sun['sunrise'])} \n**Sunset**: {to_string(sun['sunset'])}"
        )
        embed = discord.Embed(
            colour=self.bot.bot_color, title=date_string, description=description
        )
        embed.set_footer(**self.bot.bot_footer)

        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def giveaway(self, ctx: commands.Context, winners: int, *, time_string: str):
        """Start a giveaway that will last for the specified time, after that time a number of winners specified
        with the [winners] argument will be selected. The following times can be used: days (d),
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
        await ctx.send(
            f"Giveaway Ended! Congratulations to {' '.join(winner_mentions)}",
            embed=embed,
        )

    @giveaway.command(name="list")
    @commands.guild_only()
    async def giveaway_list(self, ctx: commands.Context):
        """Get a list of all current giveaways in this server

        {usage}"""
        ga_entries = [
            x for x in self.bot.ongoing_giveaways.values() if x["msg"].guild.id == ctx.guild.id
        ]
        ga_entries.sort(key=lambda x: x["limit"])

        def embed_maker(view, entries):
            ga = "\n".join(
                [
                    f"- **{entry['msg'].id}**: {format_dt(entry['limit'])} ([Link]({entry['msg'].jump_url}))"
                    for entry in entries
                ]
            )
            embed = discord.Embed(
                title=f"Giveaways ({view.page_number}/{view.page_count})",
                colour=self.bot.bot_color,
                description=ga,
            )

            embed.set_footer(**self.bot.bot_footer)

            return embed

        await paginate(ctx, ga_entries, 10, embed_maker)

    @giveaway.command(name="cancel")
    @commands.guild_only()
    async def giveaway_cancel(self, ctx: commands.Context, msg_id: int):
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

    def customise_shortcut(self, mapping):
        with open("rings/utils/shortcuts/original.str", "r", encoding="Latin-1") as f:
            content = f.read().splitlines()

        new_content = []
        for line in content:
            if not any(x in line for x in mapping):
                new_content.append(line)
                continue

            for key, value in mapping.items():
                if key in line:
                    new_content.append(line.replace(key, value))
                    break

        new_string = "\n".join(new_content)
        with open("rings/utils/shortcuts/data/data/lotr.str", "w", encoding="Latin-1") as f:
            f.write(new_string)

        file = pack_file("rings/utils/shortcuts/data", io.BytesIO())
        return discord.File(file, filename="englishpatch201_en.big")

    @commands.command()
    @commands.max_concurrency(1)
    async def shortcuts(self, ctx: commands.Context, *, new_shortcuts):
        """Customise your edain shortcuts. Pass a mapping of shortcuts to replace. At
        the moment this is only available for the english version of Edain and only for
        a single version. Current version: 4.5.5

        Possible key values: y, x, c, v, b

        {usage}

        __Examples__
        `{pre}shortcuts y=d c=r v=p`
        `{pre}shortcuts y=c c=v`
        """

        new_shortcuts_mapping = {}
        for sh in new_shortcuts.split():
            split = sh.upper().split("=")
            if split[0] not in self.shortcut_mapping:
                raise BotError(f"{split[0]} in not a valid start shortcut")

            if not split[1].isalpha():
                raise BotError(f"{split[1]} is not a valid letter")

            if len(split[1]) > 1:
                raise BotError(f"{split[1]} is more than one letter")

            new_shortcuts_mapping[f"&{split[0]}"] = f"&{split[1]}"

        async with ctx.typing():
            file = self.customise_shortcut(new_shortcuts_mapping)

        await ctx.send(
            ":white_check_mark: | Place this file in the `lang` folder of your game installation",
            file=file,
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
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
    async def on_raw_reaction_remove(self, payload):
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
    async def on_raw_message_delete(self, payload):
        if payload.message_id in self.bot.ongoing_giveaways:
            del self.ongoing_giveaways[payload.message_id]


async def setup(bot):
    await bot.add_cog(Utilities(bot))
