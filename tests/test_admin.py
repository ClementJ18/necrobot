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


async def test_grudge(ctx: commands.Context[NecroBot]):
    pass

async def test_grudge_list(ctx: commands.Context[NecroBot]):
    pass

async def test_grudge_info(ctx: commands.Context[NecroBot]):
    pass

async def test_grudge_settle(ctx: commands.Context[NecroBot]):
    pass

async def test_leave(ctx: commands.Context[NecroBot]):
    pass

async def test_guilds(ctx: commands.Context[NecroBot]):
    pass

async def test_add(ctx: commands.Context[NecroBot]):
    pass

async def test_admin_perms(ctx: commands.Context[NecroBot]):
    pass

async def test_admin_disable(ctx: commands.Context[NecroBot]):
    pass

async def test_admin_enable(ctx: commands.Context[NecroBot]):
    pass

async def test_admin_badges(ctx: commands.Context[NecroBot]):
    pass

async def test_admin_blacklist(ctx: commands.Context[NecroBot]):
    pass

async def test_pm(ctx: commands.Context[NecroBot]):
    pass

async def test_get(ctx: commands.Context[NecroBot]):
    pass

async def test_debug(ctx: commands.Context[NecroBot]):
    pass

async def test_logs(ctx: commands.Context[NecroBot]):
    pass

async def test_as(ctx: commands.Context[NecroBot]):
    pass

async def test_gate(ctx: commands.Context[NecroBot]):
    pass

async def test_pull(ctx: commands.Context[NecroBot]):
    pass
