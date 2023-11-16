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


async def test_stars(ctx: commands.Context[NecroBot]):
    pass


async def test_badges(ctx: commands.Context[NecroBot]):
    pass


async def test_title(ctx: commands.Context[NecroBot]):
    pass


async def test_profile(ctx: commands.Context[NecroBot]):
    pass


async def test_info(ctx: commands.Context[NecroBot]):
    pass


async def test_pay(ctx: commands.Context[NecroBot]):
    pass


async def test_daily(ctx: commands.Context[NecroBot]):
    pass


async def test_balance(ctx: commands.Context[NecroBot]):
    pass
