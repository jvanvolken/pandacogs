
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
                    'content': f"In one word that's less than 15 characters long, summarize this message: {message}",
                }
            ],
            'model': 'grok-beta',
            'stream': False,
            'temperature': 0.1,
        }

        try:
            await interaction.response.defer()
            
            response_json = json.loads(await Fetch(json_data))
            thread_name = response_json["choices"][0]["message"]["content"]

            thread = await interaction.channel.create_thread(
                name = thread_name,
                type = discord.ChannelType.private_thread
            )

            await interaction.response.send_message(content = f"I've created a thread for us!\n{thread.mention}")

            # response_json = json.loads(await Fetch(json_data))

            # response_message = response_json["choices"][0]["message"]["content"]
            # FM.Log(response_message)

            response_message = "TBD"
            # original_message = await interaction.edit_original_response(content=f"**Personality**\n*{personality}*\n**Message**\n*{message}*\n\n{response_message}")

            # await interaction.response.defer()

            
            original_message = await thread.send(content=f"**Personality**\n*{personality}*\n**Message**\n*{message}*\n\n{response_message}")

            message_id = original_message.id
            while True:
                # Returns true of the message is a reply to the original message
                def check(message):
                    FM.Log(message)
                    FM.Log(message.reference)
                    FM.Log(f"{message.reference.message_id} <> {message_id}")
                    return message.reference and message.reference.message_id == message_id

                # Wait for a reply in accordance with the check function
                FM.Log("PRE-CHECK")
                msg: discord.Message = await self.bot.wait_for('message', check = check)#, timeout=10.0)
                FM.Log("POST-CHECK")

                if msg is None:
                    FM.Log("Thanks for chatting!")
                    await original_message.channel.send("Thanks for chatting!")
                    break

                new_response = await msg.reply(content=f"You replied with: {msg.content}")
                message_id = new_response.id

        except Exception as e:
            FM.Log(str(e), LogType.Error)