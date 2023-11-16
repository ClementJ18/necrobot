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


async def test_enable(ctx: commands.Context[NecroBot]):
    pass


async def test_disable(ctx: commands.Context[NecroBot]):
    pass


async def test_speak(ctx: commands.Context[NecroBot]):
    pass


async def test_purge(ctx: commands.Context[NecroBot]):
    pass


async def test_warn(ctx: commands.Context[NecroBot]):
    pass
