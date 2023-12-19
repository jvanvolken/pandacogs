from .autorolerpro import AutoRolerPro

async def setup(bot):
    await bot.add_cog(AutoRolerPro(bot))