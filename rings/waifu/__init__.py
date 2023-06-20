from .waifu import Flowers


async def setup(bot):
    await bot.add_cog(Flowers(bot))
