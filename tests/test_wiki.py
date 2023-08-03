from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from discord.ext import commands

from rings.utils.utils import BotError

if TYPE_CHECKING:
    from bot import NecroBot


async def test_lotr(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("lotr")

    await ctx.invoke(command, article_name="Finrod Felagund")
    await ctx.invoke(command, article_name="Fellowship")

    with pytest.raises(BotError):
        await ctx.invoke(command, article_name="AZKEAZEAZ")


async def test_wiki(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("wiki")

    await ctx.invoke(command, sub_wiki="disney", article_name="Donald Duck")
    await ctx.invoke(command, sub_wiki="transformers", article_name="Optimus")

    with pytest.raises(BotError):
        await ctx.invoke(command, sub_wiki="disney", article_name="AZKEAZEAZ")

    with pytest.raises(BotError):
        await ctx.invoke(command, sub_wiki="azeazeaeaz", article_name="Donald")


async def test_aotr(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("aotr")

    await ctx.invoke(command, article_name="Aragorn")
    await ctx.invoke(command, article_name="Castellans")

    with pytest.raises(BotError):
        await ctx.invoke(command, article_name="AZKEAZEAZ")


async def test_edain(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("edain")

    await ctx.invoke(command, article_name="Aragorn")
    await ctx.invoke(command, article_name="Castellans")

    with pytest.raises(BotError):
        await ctx.invoke(command, article_name="AZKEAZEAZ")


async def test_edain_faq(ctx: commands.Context[NecroBot]):
    command = ctx.bot.get_command("edain faq")

    await ctx.invoke(command, question="When arnor")
    await ctx.invoke(command, question="When 2.02")

    with pytest.raises(BotError):
        await ctx.invoke(command, question="AZKEAZEAZ")
