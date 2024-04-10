from .mediadownloader import MediaDownloader

async def setup(bot):
    await bot.add_cog(MediaDownloader(bot))