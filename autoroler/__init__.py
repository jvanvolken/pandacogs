from .autoroler import AutoRoler

async def setup(bot):
    await bot.add_cog(AutoRoler(bot))