
# Discord Bot Libraries
import discord
from redbot.core import commands

class MediaDownloader(commands.Cog):
    """My custom cog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        """Hello World Reply!"""

        # Get member that sent the command
        member: discord.Member = ctx.message.author
        guild: discord.Guild = ctx.message.guild

        await ctx.reply("Hello World!")
        