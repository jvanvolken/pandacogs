
# Discord Bot Libraries
import discord
from redbot.core import commands

class MediaDownloader(commands.Cog):
    """My custom cog"""

    def __init__(self, bot):
        # Instantiates the bot
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        """Hello World Reply!"""

        # Replied with a simple Hello World!
        await ctx.reply("Hello World!")
    
    @commands.command()
    async def get_media(self, ctx, arg: str):
        """Get the media from the last 200 messages\n Usage: !get_media <channel>"""

        # Get member that sent the command and the guild in which the command was sent
        member: discord.Member = ctx.message.author
        guild: discord.Guild = ctx.message.guild

        # Try and parse the provided argument to get a channel ID from it.
        channel_id = arg.replace('#', '').replace('<', '').replace('>', '')
        channel = guild.get_channel(int(channel_id))

        # If the channel ID was valid, continue
        if channel:
            # Collect a list of messages from the channel's history (with a limit)
            messages = [msg async for msg in channel.history(limit=200)]

            # Loop through the messages and count the attachments if any
            media_count = 0
            for msg in messages:
                if msg.attachments:
                    media_count += len(msg.attachments)

            # Reply with the media count, giving a special case for '1'
            if media_count == 1:
                await ctx.reply(f"Within the last `200` messages in {arg}, there is `{media_count}` attachment!")
            else:
                await ctx.reply(f"Within the last `200` messages in {arg}, there are `{media_count}` attachments!")
        else:
            # Tell the user that they provided an invalid channel.
            await ctx.reply(f"Could not find the channel, {arg}! Please try again!")
