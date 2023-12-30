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
    pass

async def test_choose_mult(ctx: commands.Context[NecroBot]):
    pass

async def test_coin(ctx: commands.Context[NecroBot]):
    pass

async def test_roll(ctx: commands.Context[NecroBot]):
    pass

async def test_8ball(ctx: commands.Context[NecroBot]):
    pass
