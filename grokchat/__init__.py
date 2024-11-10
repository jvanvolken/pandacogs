from .grokbot import GrokBot

async def setup(bot):
    await bot.add_cog(GrokBot(bot))