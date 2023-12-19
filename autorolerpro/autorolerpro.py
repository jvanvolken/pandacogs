# Image and File Manipulation Libraries
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFilter, ImageFont

# Discord Bot Libraries
import discord
from redbot.core import commands

# Cog Directory in Appdata
docker_cog_path = "/data/cogs/AutoRoler"


class AutoRolerPro(commands.Cog):
    """My custom cog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def list_games(self, ctx):
        """Lists the collected game roles for the server."""
        
        # Get important information about the context of the command
        channel = ctx.channel
        author = ctx.message.author

        # Sends message in the command's origin channel
        await channel.send(f"This is where I'd list the games if I had any!!")

    @discord.Client.event
    async def on_member_update(previous, current):

        # Get important information about the context of the command
        channel = current.get_channel(665572348350693406)
        member_name = current.display_name.encode().decode('ascii','ignore')

        # role = discord.utils.get(current.guild.roles, name="Gamer")
        games = ["overwatch", "rocket league", "minecraft"]

        # When somebody starts or stops playing a game
        if current.activity and current.activity.name.lower() in games:
            await channel.send(f"{member_name} started playing {current.activity.name}!")
        elif previous.activity and previous.activity.name.lower() in games and not current.activity:
            await channel.send(f"{member_name} stopped playing {current.activity.name}!")