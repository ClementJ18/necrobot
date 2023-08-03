from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from discord.ext import commands

from rings.utils.utils import BotError

if TYPE_CHECKING:
    from bot import NecroBot


async def test_shuffle(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("shuffle")

    await ctx.invoke(command, sentence="zarb")

    with pytest.raises(TypeError):
        await ctx.invoke(command)


async def test_define(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("define")

    await ctx.invoke(command, word="sand")

    with pytest.raises(BotError):
        await ctx.invoke(command, word="efzfzj")

    with pytest.raises(BotError):
        await ctx.invoke(command, word="soud")

    with pytest.raises(commands.CommandOnCooldown):
        await ctx.invoke(command, word="sand")
        await command.reset_cooldown(ctx)


async def test_ud(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("ud")

    await ctx.invoke(command, word="national day")

    with pytest.raises(BotError):
        await ctx.invoke(command, word="abzdahz")
