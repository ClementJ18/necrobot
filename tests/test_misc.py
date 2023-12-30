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

async def test_cat(ctx: commands.Context[NecroBot]):
    pass

async def test_dog(ctx: commands.Context[NecroBot]):
    pass

async def test_fight(ctx: commands.Context[NecroBot]):
    pass

async def test_matchups(ctx: commands.Context[NecroBot]):
    pass

async def test_matchups_reset(ctx: commands.Context[NecroBot]):
    pass

async def test_matchups_logs(ctx: commands.Context[NecroBot]):
    pass

async def test_message(ctx: commands.Context[NecroBot]):
    pass

async def test_delete(ctx: commands.Context[NecroBot]):
    pass

async def test_stats(ctx: commands.Context[NecroBot]):
    pass