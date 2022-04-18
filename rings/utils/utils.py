import discord
from discord.ext import commands

import re
import datetime
import itertools

class BotError(Exception):
    pass

def check_channel(channel):
    if not channel.permissions_for(channel.guild.me).send_messages:
        raise BotError("I need permissions to send messages in this channel")

def has_welcome(bot, member):
    return bot.guild_data[member.guild.id]["welcome-channel"] and bot.guild_data[member.guild.id]["welcome"]

def has_goodbye(bot, member):
    return bot.guild_data[member.guild.id]["welcome-channel"] and bot.guild_data[member.guild.id]["goodbye"]

def has_automod(bot, message):
    if not bot.guild_data[message.guild.id]["automod"]:
        return False
        
    if message.author.id in bot.guild_data[message.guild.id]["ignore-automod"]:
        return False
        
    if message.channel.id in bot.guild_data[message.guild.id]["ignore-automod"]:
        return False
    
    role_ids = [role.id for role in message.author.roles]
    if any(x in role_ids for x in bot.guild_data[message.guild.id]["ignore-automod"]):
        return False
        
    return True

def format_dt(dt: datetime.datetime, /, style: str = None) -> str:
    if style is None:
        return f'<t:{int(dt.timestamp())}>'
    return f'<t:{int(dt.timestamp())}:{style}>'

def time_string_parser(message):
    if "in " in message:
        text, sep, time = message.rpartition("in ")
        sleep = time_converter(time)

        if not sep:
            raise BotError("Something went wrong, you need to use the format: **<optional_message> in <time>**")

        return text, sleep, time

    if "on " in message:
        text, sep, time = message.rpartition("on ")
        sleep = date_converter(time)

        if not sep:
            raise BotError("Something went wrong, you need to use the format: **<optional_message> on <time>**")

        return text, sleep, time

    raise BotError("Something went wrong, you need to use the format: **<optional_message> in|on <time>**")
    
async def react_menu(ctx, entries, per_page, generator, *, page=0, timeout=300):
    max_pages = max(0, ((len(entries)-1)//per_page))
    if not entries:
        raise BotError("No entries in this list")
    
    subset = entries[page*per_page:(page+1)*per_page]
    msg = await ctx.send(embed=generator((page + 1, max_pages + 1), subset[0] if per_page == 1 else subset))
    if len(entries) <= per_page:
        return
    
    react_list = ["\N{BLACK LEFT-POINTING TRIANGLE}", "\N{BLACK SQUARE FOR STOP}", "\N{BLACK RIGHT-POINTING TRIANGLE}"]
    for reaction in react_list:
        await msg.add_reaction(reaction)

    async def handler():
        try:
            await msg.clear_reactions()
        except discord.errors.NotFound:
            pass

    while True: 
        def check(r, u):
            return u == ctx.message.author and r.emoji in react_list and msg.id == r.message.id

        reaction, user = await ctx.bot.wait_for(
            "reaction_add", 
            check=check, 
            timeout=timeout, 
            handler=handler, 
            propagate=False
        )

        if reaction.emoji == "\N{BLACK SQUARE FOR STOP}":
            return await msg.clear_reactions()
            
        if reaction.emoji == "\N{BLACK LEFT-POINTING TRIANGLE}":
            page -= 1
            if page < 0:
                page = max_pages
        elif reaction.emoji == "\N{BLACK RIGHT-POINTING TRIANGLE}":
            page += 1
            if page > max_pages:
                page = 0

        try:
            await reaction.remove(user)
        except discord.Forbidden:
            pass
        
        subset = entries[page*per_page:(page+1)*per_page]
        await msg.edit(embed=generator((page + 1, max_pages + 1), subset[0] if per_page == 1 else subset))


async def get_pre(bot, message):
    """If the guild has set a custom prefix we return that and the ability to mention alongside regular 
    admin prefixes if not we return the default list of prefixes and the ability to mention."""
    if not isinstance(message.channel, discord.DMChannel):
        guild_pre = bot.guild_data[message.guild.id]["prefix"]
        if guild_pre != "":
            guild_pre = map(''.join, itertools.product(*((c.upper(), c.lower()) for c in guild_pre)))
            return commands.when_mentioned_or(*guild_pre)(bot, message)

    return commands.when_mentioned_or(*bot.prefixes)(bot, message)
    
def time_converter(argument):
    time = 0

    pattern = re.compile(r"([0-9]*(?:\.|\,)?[0-9]*)\s?([dhms])")
    matches = re.findall(pattern, argument)

    convert = {
        "d" : 86400,
        "h" : 3600,
        "m" : 60,
        "s" : 1
    }

    for match in matches:
        if not match[0]:
            continue
        
        time += convert[match[1]] * float(match[0].replace(",", "."))

    return time

def date_converter(argument):
    date_time = argument.split(" ")
    if len(date_time) > 2:
        raise BotError("Invalid date time format")

    seconds = 0
    minutes = 0
    hours = 0
    days = 0
    months = 0
    years = 0
    now = datetime.datetime.now()
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
        year = years or now.year,
        month = months or now.month,
        day = days or now.day,
        hour = hours or now.hour,
        minute = minutes or now.minute,
        second = seconds or now.second
    )

    return (date - now).total_seconds()

def midnight():
    """Get the number of seconds until midnight."""
    tomorrow = datetime.datetime.now() + datetime.timedelta(1)
    time = datetime.datetime(
        year=tomorrow.year, month=tomorrow.month, 
        day=tomorrow.day, hour=0, minute=0, second=0
    )
    return time - datetime.datetime.now()

def default_settings():
    return {
        "blacklist": [],
        "news": [],
        "disabled": [],
        "shop": [],
        "messages": {},
        "days": 0
    }
