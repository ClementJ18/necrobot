from __future__ import annotations

import datetime
import itertools
import re
import traceback
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from bot import NecroBot


class BotError(Exception):
    pass


class DatabaseError(Exception):
    def __init__(self, message: str, query: str = None, args=()):
        super().__init__(message)
        self.message = message
        self.query = query
        self.args = args

    def embed(self, bot: NecroBot):
        formatted = traceback.format_exception(type(self), self, self.__traceback__, chain=False)
        msg = f"```py\n{' '.join(formatted)}\n```"

        embed = discord.Embed(title="DB Error", description=msg, colour=bot.bot_color)
        embed.add_field(name="Event", value=self.message, inline=False)
        embed.add_field(name="Query", value=self.query, inline=False)
        embed.add_field(name="Arguments", value=self.args, inline=False)
        embed.set_footer(**bot.bot_footer)

        return embed

    def __str__(self):
        return self.message


def check_channel(channel: discord.TextChannel):
    if not channel.permissions_for(channel.guild.me).send_messages:
        raise BotError("I need permissions to send messages in this channel")


def format_dt(dt: datetime.datetime, /, style: str = None) -> str:
    if style is None:
        return f"<t:{int(dt.timestamp())}>"
    return f"<t:{int(dt.timestamp())}:{style}>"


def time_string_parser(message: str):
    if "in " in message:
        text, sep, time = message.rpartition("in ")
        sleep = time_converter(time)

        if not sep:
            raise BotError(
                "Something went wrong, you need to use the format: **<optional_message> in <time>**"
            )

        return text, sleep, time

    if "on " in message:
        text, sep, time = message.rpartition("on ")
        sleep = date_converter(time)

        if sep:
            raise BotError(
                "Something went wrong, you need to use the format: **<optional_message> on <time>**"
            )

        return text, sleep, time

    raise BotError(
        "Something went wrong, you need to use the format: **<optional_message> in|on <time>**"
    )


async def get_pre(bot: NecroBot, message: discord.Message):
    """If the guild has set a custom prefix we return that and the ability to mention alongside regular
    admin prefixes if not we return the default list of prefixes and the ability to mention."""
    if not isinstance(message.channel, discord.DMChannel):
        guild_pre = bot.guild_data[message.guild.id]["prefix"]
        if guild_pre != "":
            guild_pre = map(
                "".join, itertools.product(*((c.upper(), c.lower()) for c in guild_pre))
            )
            return commands.when_mentioned_or(*guild_pre)(bot, message)

    return commands.when_mentioned_or(*bot.prefixes)(bot, message)


def time_converter(argument: str) -> int:
    time = 0

    pattern = re.compile(r"([0-9]*(?:\.|\,)?[0-9]*)\s?([dhms])")
    matches = re.findall(pattern, argument)

    convert = {"d": 86400, "h": 3600, "m": 60, "s": 1}

    for match in matches:
        if not match[0]:
            continue

        time += convert[match[1]] * float(match[0].replace(",", "."))

    return time


def date_converter(argument: str):
    date_time = argument.split(" ")
    if len(date_time) > 2:
        raise BotError("Invalid date time format")

    seconds = 0
    minutes = 0
    hours = 0
    days = 0
    months = 0
    years = 0
    now = datetime.datetime.now(datetime.timezone.utc)
    for string in date_time:
        if ":" in string:
            hour_minutes = string.split(":")
            if len(hour_minutes) != 2:
                raise BotError("Invalid time format")

            try:
                hours = int(hour_minutes[0])
                minutes = int(hour_minutes[1])
            except ValueError as e:
                raise BotError("Invalid time format") from e

        if "/" in string:
            year_month_day = string.split("/")
            if len(year_month_day) != 3:
                raise BotError("Invalid date format")

            try:
                years = int(year_month_day[0])
                months = int(year_month_day[1])
                days = int(year_month_day[2])
            except ValueError as e:
                raise BotError("Invalid date format") from e

    date = datetime.datetime(
        year=years or now.year,
        month=months or now.month,
        day=days or now.day,
        hour=hours or now.hour,
        minute=minutes or now.minute,
        second=seconds or now.second,
        tzinfo=datetime.timezone.utc,
    )

    return (date - now).total_seconds()


def midnight():
    """Get the number of seconds until midnight."""
    tomorrow = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(1)
    time = datetime.datetime(
        year=tomorrow.year,
        month=tomorrow.month,
        day=tomorrow.day,
        hour=0,
        minute=0,
        second=0,
        tzinfo=datetime.timezone.utc,
    )
    return time - datetime.datetime.now(datetime.timezone.utc)


def default_settings():
    return {
        "blacklist": [],
        "news": [],
        "disabled": [],
        "shop": [],
        "messages": {},
        "day": 0,
    }


class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __str__(self):
        return self.get("str")


def build_format_dict(
    *,
    guild: discord.Guild = None,
    member: discord.Member = None,
    channel: discord.TextChannel = None,
):
    arg_dict = dict()

    if guild is not None:
        guild_dict = dotdict(
            {
                "str": str(guild),
                "name": str(guild.name),
                "id": str(guild.id),
                "created_at": str(guild.created_at),
                "member_count": str(guild.member_count),
            }
        )

        arg_dict["server"] = guild_dict

    if member is not None:
        member_dict = dotdict(
            {
                "str": str(member),
                "display_name": str(member.display_name),
                "name": str(member.name),
                "discriminator": str(member.discriminator),
                "joined_at": str(member.joined_at),
                "id": str(member.id),
                "mention": str(member.mention),
                "created_at": str(member.created_at),
            }
        )

        arg_dict["member"] = member_dict

    if channel is not None:
        channel_dict = dotdict(
            {
                "str": str(channel),
                "name": str(channel.name),
                "id": str(channel.id),
                "topic": str(channel.topic),
                "mention": str(channel.mention),
            }
        )

        arg_dict["channel"] = channel_dict

    return arg_dict
