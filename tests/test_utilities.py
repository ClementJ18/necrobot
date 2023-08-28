from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

import discord
import pytest
from discord.ext import commands

from rings.utils.utils import BotError
from tests.utils import delay

if TYPE_CHECKING:
    from bot import NecroBot


async def test_giveaway(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("giveaway")
    await ctx.invoke(command, winner=1, time_string="15s")

    with pytest.raises(BotError):
        await ctx.invoke(command, winner=1, time_string="0s")

    _ = asyncio.create_task(delay(5, ctx.invoke(command, winner=1, time_string="10s")))

    message: discord.Message = await ctx.bot.wait_for(
        "message",
        check=lambda m: m.author.id == ctx.bot.user.id and m.channel.id == ctx.channel.id,
    )
    ctx.bot.ongoing_giveaways[message.id]["entries"].append(ctx.bot.user.id)

    await ctx.invoke(ctx.bot.get_command("giveaway list"))

    command_cancel = ctx.bot.get_command("giveaway cancel")
    _ = asyncio.create_task(delay(5, ctx.invoke(command, winner=1, time_string="60s")))
    message: discord.Message = await ctx.bot.wait_for(
        "message",
        check=lambda m: m.author.id == ctx.bot.user.id and m.channel.id == ctx.channel.id,
    )

    await ctx.invoke(command_cancel, msg_id=message.id)

    with pytest.raises(BotError):
        await ctx.invoke(command_cancel, msg_id=message.id)


async def test_sun(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("sun")

    await ctx.invoke(command, city="London")
    await ctx.invoke(command, city="London", date="22/04/2019")

    with pytest.raises(BotError):
        await ctx.invoke(command, city="AZEAZEAZ")


async def test_leaderboard(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("leaderboard")
    command_message = ctx.bot.get_command("leaderboard message")

    await ctx.invoke(command_message, message="Leaderboard for cool kids")

    with pytest.raises(BotError):
        await ctx.invoke(command_message, message="a" * 201)

    command_symbol = ctx.bot.get_command("leaderboard symbol")

    await ctx.invoke(command_symbol, symbol=":eyes:")

    with pytest.raises(BotError):
        await ctx.invoke(command_symbol, symbol="a" * 51)

    command_award = ctx.bot.get_command("leaderboard award")

    await ctx.invoke(command_award, user=ctx.bot.user, points=random.randint(-200, 0))
    await ctx.invoke(command_award, user=ctx.bot.user, points=random.randint(0, 200))

    await ctx.invoke(command)


async def test_queue(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("q")
    command_clear = ctx.bot.get_command("q clear")
    command_end = ctx.bot.get_command("q end")
    command_next = ctx.bot.get_command("q next")
    command_me = ctx.bot.get_command("q me")
    command_start = ctx.bot.get_command("q start")

    await ctx.invoke(command_clear)

    with pytest.raises(BotError):
        await ctx.invoke(command_next)

    with pytest.raises(BotError):
        await ctx.invoke(command_me)

    await ctx.invoke(command_start)

    with pytest.raises(BotError):
        await ctx.invoke(command)

    await ctx.invoke(command_me)
    await ctx.invoke(command)
    await ctx.invoke(command_next)
    await ctx.invoke(command_me)

    await ctx.invoke(command_end)
    await ctx.invoke(command_next)


async def test_remindme(ctx: commands.Context[NecroBot]):
    command = await ctx.bot.get_command("remindme")


async def test_today(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("today")

    await ctx.invoke(command)
    await ctx.invoke(command, date="14/02")
    await ctx.invoke(command, choice="events")
    await ctx.invoke(command, choice="events", date="14/02")
    await ctx.invoke(command, choice="deaths")
    await ctx.invoke(command, choice="deaths", date="14/02")
    await ctx.invoke(command, choice="births")
    await ctx.invoke(command, choice="births", date="14/02")


async def test_avatar(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("avatar")

    await ctx.invoke(command)
    await ctx.invoke(command, user=ctx.author)


async def test_serverinfo(ctx: commands.Context[NecroBot]):
    await ctx.invoke(ctx.bot.get_command("serverinfo"))


async def test_calc(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("calc")

    await ctx.invoke(command, equation="2+2")
    await ctx.invoke(command, equation="(4 + 5) * 3 / (2 - 1)")

    with pytest.raises(BotError):
        await ctx.invoke(command, equation="ctx.bot._http.token")
