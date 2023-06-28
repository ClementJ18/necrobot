from .decisions import Decisions


async def setup(bot):
    await bot.add_cog(Decisions(bot))
