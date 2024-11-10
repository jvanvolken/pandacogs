
import requests
import discord

from redbot.core import commands, bot, app_commands

# Initializes intents
intents = discord.Intents(messages=True, guilds=True, members = True, presences = True)

# Initializes client with intents
client = discord.Client(intents = intents)

class GrokBot(commands.Cog):
    """GrokBot"""
    def __init__(self, bot: bot.Red):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(personality="Describe Benjamin's personality for this response!", message="Your message to Benjamin!")
    async def benjamin(self, interaction: discord.Interaction, personality: str, message: str):
        """Replies to a message!"""

        # Get member that sent the command
        member = interaction.user
        guild  = interaction.guild

        await interaction.response.send_message(f"Thank you for giving me the personality of '{personality}' along with your message, '{message}'")