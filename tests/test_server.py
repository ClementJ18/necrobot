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


async def test_poll(ctx: commands.Context[NecroBot]):
    pass


async def test_starboard(ctx: commands.Context[NecroBot]):
    pass


async def test_giveme(ctx: commands.Context[NecroBot]):
    pass


async def test_broadcast(ctx: commands.Context[NecroBot]):
    pass


async def test_auto_role(ctx: commands.Context[NecroBot]):
    pass


async def test_prefix(ctx: commands.Context[NecroBot]):
    pass


async def test_farewell(ctx: commands.Context[NecroBot]):
    pass


async def test_welcome(ctx: commands.Context[NecroBot]):
    pass


async def test_settings(ctx: commands.Context[NecroBot]):
    pass


async def test_ignore(ctx: commands.Context[NecroBot]):
    pass


async def test_automod(ctx: commands.Context[NecroBot]):
    pass


async def test_demote(ctx: commands.Context[NecroBot]):
    pass


async def test_promote(ctx: commands.Context[NecroBot]):
    pass


async def test_permissions(ctx: commands.Context[NecroBot]):
    pass
