from __future__ import annotations

import typing

from .social import Social

if typing.TYPE_CHECKING:
    from bot import NecroBot


async def setup(bot: NecroBot):
    await bot.add_cog(Social(bot))
