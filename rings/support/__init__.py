from __future__ import annotations

import typing

from .support import Support

if typing.TYPE_CHECKING:
    from bot import NecroBot


async def setup(bot: NecroBot):
    await bot.add_cog(Support(bot))
