from __future__ import annotations

import typing

from .waifu import Flowers

if typing.TYPE_CHECKING:
    from bot import NecroBot


async def setup(bot: NecroBot):
    await bot.add_cog(Flowers(bot))
