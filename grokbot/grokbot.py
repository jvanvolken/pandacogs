
import json
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

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer xai-NibicvvthU6cC5C4H2bybwWS6EuNmbCFETUyZIg9xeNnBLnHEl1O9mn3nBcBeG2NfCPkqhRWfde4bTxu',
        }

        json_data = {
            'messages': [
                {
                    'role': 'system',
                    'content': f"{personality}",
                },
                {
                    'role': 'user',
                    'content': f"{message}",
                },
            ],
            'model': 'grok-beta',
            'stream': False,
            'temperature': 0,
        }

        response = requests.post('https://api.x.ai/v1/chat/completions', headers=headers, json=json_data)
        data_json = json.loads(response.content) 
        response_message = data_json["choices"][0]["message"]["content"]

        await interaction.response.send_message(f"**Personality**\n*{personality}*\n**Message**\n*{message}*\n\n{response_message}")