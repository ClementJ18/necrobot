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


async def test_choose(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("choose")

    await ctx.invoke(command, choices="Bob, John Smith, Mary")
    await ctx.invoke(command, choices="1, 2")
    await ctx.invoke(command, choices="I | like, hate | tico, kittycat")


async def test_choose_mult(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("choose mult")

    await ctx.invoke(command, count=2, choices="Bob, John, Smith, Mary")
    await ctx.invoke(command, count=2, choices="Elves, Men, Dwarves | Legolas, Gimli, Aragorn")


async def test_coin(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("coin")

    await ctx.invoke(command)
    await ctx.invoke(command)

    await ctx.bot.db.update_money(ctx.author.id, add=50)
    await ctx.invoke(command, choice="t", bet=50)


async def test_roll(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("roll")

    await ctx.invoke(command)

    await ctx.invoke(command, dices="3d8")
    await ctx.invoke(command, dices="3d8+6")
    await ctx.invoke(command, dices="500d8+6")


async def test_ball8(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("8ball")

    await ctx.invoke(command)
    await ctx.invoke(command, message="test")
