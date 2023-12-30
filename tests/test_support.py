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

async def test_about(ctx: commands.Context[NecroBot]):
    pass

async def test_report(ctx: commands.Context[NecroBot]):
    pass

async def test_tutorial(ctx: commands.Context[NecroBot]):
    pass

async def test_privacy(ctx: commands.Context[NecroBot]):
    pass