
import asyncio
import json
import aiohttp
import discord

from redbot.core import commands, bot, app_commands

# Initializes intents
intents = discord.Intents(messages=True, guilds=True, members = True, presences = True)

# Initializes client with intents
client = discord.Client(intents = intents)

async def Fetch(body):
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method="POST",
            url="https://api.x.ai/v1/chat/completions",
            headers={
                "Content-Type":"application/json",
                "Authorization":"Bearer xai-NibicvvthU6cC5C4H2bybwWS6EuNmbCFETUyZIg9xeNnBLnHEl1O9mn3nBcBeG2NfCPkqhRWfde4bTxu"
            },
            json=body
        ) as response:
            return await response.read()
            
class GrokBot(commands.Cog):
    """GrokBot"""
    def __init__(self, bot: bot.Red):
        self.bot = bot
                
    @app_commands.command()
    @app_commands.describe(personality="Describe Benjamin's personality for this response!", message="Your message to Benjamin!")
    async def chat(self, interaction: discord.Interaction, personality: str, message: str):
        """Replies to a message!"""

        json_data = {
            'messages': [
                {
                    'role': 'system',
                    'content': f"{personality}",
                },
                {
                    'role': 'user',
                    'content': f"{message} - limit your response to a maximum of 2000 characters",
                },
            ],
            'model': 'grok-beta',
            'stream': False,
            'temperature': 0.1,
        }

        print("-- RESPONSE ".ljust(70, '-'))
        try:
            response_json = json.loads(await Fetch(json_data))
            print(response_json)

            response_message = response_json["choices"][0]["message"]["content"]
            
            await interaction.followup.send(f"**Personality**\n*{personality}*\n**Message**\n*{message}*\n\n{response_message}")

            # await interaction.response.defer()
            # asyncio.sleep()

            # await interaction.response.send_message(f"**Personality**\n*{personality}*\n**Message**\n*{message}*\n\n{response_message}")
        except Exception as e:
            print(str(e))
            # await interaction.response.defer()
            # asyncio.sleep()
            # await interaction.followup.send(f"Command failed!\n{str(e)[:2000]}", ephemeral=True)
            # await interaction.response.send_message(f"Command failed!\n{str(e)[:2000]}", ephemeral=True)