
import requests
import discord

from redbot.core import commands, bot, app_commands


class GrokBot(commands.Cog):
    """GrokBot"""
    def __init__(self, bot: bot.Red):
        self.bot = bot

    @app_commands.describe(personality="Describe who benjamin should be responding as.")
    async def benjamin(self, interaction: discord.Interaction, personality: str = None):
        """Replies to a message!"""

        # Get member that sent the command
        member = interaction.user
        guild  = interaction.guild

        await interaction.response.send_message(f"Thank you for giving me the personality of {personality}")