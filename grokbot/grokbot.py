
import asyncio
import json
import aiohttp
import discord

from redbot.core import commands, bot, app_commands
from .filemanager import FileManager, LogType

# Initializes intents
intents = discord.Intents(messages=True, guilds=True, members = True, presences = True)

# Initializes client with intents
client = discord.Client(intents = intents)

FM = FileManager({
    'Authorization': "SECRET / CHANGE ME"
})

async def Fetch(body):
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method="POST",
            url="https://api.x.ai/v1/chat/completions",
            headers={
                "Content-Type":"application/json",
                "Authorization":f"Bearer {FM.config['Authorization']}"
            },
            json=body
        ) as response:
            return await response.read()

class GrokBot(commands.Cog):
    """GrokBot"""
    def __init__(self, bot: bot.Red):
        self.bot = bot
        FM.Log("-- Successfully initialized GrokBot! ".ljust(70, '-'))

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
                    'content': f"{message} - limit your response to a maximum of 1000 characters",
                }
            ],
            'model': 'grok-beta',
            'stream': False,
            'temperature': 0.1,
        }

        try:
            await interaction.response.send_message(content="*let me think...*")

            # response_json = json.loads(await Fetch(json_data))

            # response_message = response_json["choices"][0]["message"]["content"]
            # FM.Log(response_message)

            original_message = await interaction.edit_original_response(content=f"**Personality**\n*{personality}*\n**Message**\n*{message}*\n\nTBD")

            message_id = original_message.id
            while True:
                # Returns true of the message is a reply to the original message
                def check(message):
                    return message.reference and message.reference.message_id == message_id
            
                # Wait for a reply in accordance with the check function
                msg: discord.Message = await self.bot.wait_for('message', check = check, timeout=10.0)

                message_id = msg.id
                if msg is None:
                    await original_message.channel.send("Thanks for chatting!")
                    break

                await msg.reply(content=f"You replied with: {msg.content}")
        except Exception as e:
            FM.Log(str(e), LogType.Error)