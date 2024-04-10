
import json
import os

# Discord Bot Libraries
import discord
from redbot.core import commands

# Cog Directory in Appdata
docker_cog_path  = "/data/cogs/MediaDownloader"
config_file      = f"{docker_cog_path}/config.json"

# Create the docker_cog_path if it doesn't already exist
os.makedirs(docker_cog_path, exist_ok = True)

default_config = {
    "Archive Directory": ""
}

# Initializes config 
if os.path.isfile(config_file):
    with open(config_file, "r") as fp:
        config = json.load(fp)
else:
    config = default_config
    with open(config_file, "w") as fp:
        json.dump(config, fp, indent = 2, default = str, ensure_ascii = False)

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


    @commands.command()
    async def check_path(self, ctx):
        """Checks path for existance"""

        path = docker_cog_path
        if os.path.exists(path):
            await ctx.channel.send(f"{path} exists!")
        else:
            await ctx.channel.send(f"{path} does not exist!")

        path = "/data"
        if os.path.exists(path):
            await ctx.channel.send(f"{path} exists!")
        else:
            await ctx.channel.send(f"{path} does not exist!")

        path = "/archive"
        if os.path.exists(path):
            await ctx.channel.send(f"{path} exists!")
        else:
            await ctx.channel.send(f"{path} does not exist!")