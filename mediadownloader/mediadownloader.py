
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
    
    @commands.command()
    async def get_media(self, ctx, channel):
        """Get the media from the last 200 messages\n Usage: !get_media <channel>"""

        # Get member that sent the command
        member: discord.Member = ctx.message.author
        guild: discord.Guild = ctx.message.guild



        if channel.id and guild.get_channel(channel.id):
            await ctx.reply(f"{channel} is a channel!")
        else:
            await ctx.reply(f"{channel} is not a channel!")

        # messages = await ctx.channel.history(limit=200).flatten()

        # for msg in messages:
        #     if word in msg.content:
        #         print(msg.jump_url)