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

async def test_dadjoke(ctx: commands.Context[NecroBot]):
    pass

async def test_riddle(ctx: commands.Context[NecroBot]):
    pass

async def test_tarot(ctx: commands.Context[NecroBot]):
    pass

async def test_rr(ctx: commands.Context[NecroBot]):
    pass

async def test_lotrfact(ctx: commands.Context[NecroBot]):
    pass

async def test_pokefusion(ctx: commands.Context[NecroBot]):
    pass

async def test_got(ctx: commands.Context[NecroBot]):
    pass
