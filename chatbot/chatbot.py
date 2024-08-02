
import discord
from redbot.core import commands, bot, app_commands


class ChatBot(commands.Cog):
    """ChatBot"""
    def __init__(self, bot: bot.Red):
        self.bot = bot


    @app_commands.command()
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello World!", ephemeral=True)
        
