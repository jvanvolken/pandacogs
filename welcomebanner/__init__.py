from .welcomebanner import WelcomeBanner

async def setup(bot):
    await bot.add_cog(WelcomeBanner(bot))