
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
    async def get_media(self, ctx, arg: str):
        """Get the media from the last 200 messages\n Usage: !get_media <channel>"""

        # Get member that sent the command
        member: discord.Member = ctx.message.author
        guild: discord.Guild = ctx.message.guild

        channel_id = arg.replace('#', '').replace('<', '').replace('>', '')
        channel = guild.get_channel(int(channel_id))

        if channel:
            messages = [msg async for msg in channel.history(limit=200)]

            media_count = 0
            for msg in messages:
                if msg.attachments:
                    media_count += len(msg.attachments)

            if media_count == 1:
                await ctx.reply(f"Within the last `200` messages in {arg}, there is `{media_count}` attachment!")
            else:
                await ctx.reply(f"Within the last `200` messages in {arg}, there are `{media_count}` attachments!")
        else:
            await ctx.reply(f"Could not find the channel, {arg}!")
