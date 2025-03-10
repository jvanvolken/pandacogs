
import json
import aiohttp
import discord
import re

from redbot.core import commands, bot, app_commands
from .filemanager import FileManager, LogType

# Initializes intents
intents = discord.Intents(messages=True, guilds=True, members = True, presences = True)

# Initializes client with intents
client = discord.Client(intents = intents)

FM = FileManager({
    'Authorization': "SECRET / CHANGE ME",
    "DefaultPersonality": "You are Grok, a kind and helpful chat bot.",
    "BotName": "Grok"
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
    @app_commands.describe(personality=f"Describe {FM.config['BotName']}'s personality for this chat!", message=f"Your message to {FM.config['BotName']}!")
    async def chat(self, interaction: discord.Interaction, message: str, personality: str = FM.config['DefaultPersonality']):
        """Replies to a message!"""

        json_data = {
            'messages': [
                {
                    'role': 'system',
                    'content': f"{personality}. Answer in this format: **Summary:** [replace with a 1 or 2 word summary that's LESS than 15 CHARACTERS LONG]\n\n[replace with the formatted response]",
                },
                {
                    'role': 'user',
                    'content': f"{message} - limit your response to a maximum of 1000 characters",
                }
            ],
            'model': 'grok-beta',
            'stream': False,
            'temperature': 0.2,
        }

        try:
            await interaction.response.defer()

            response_json = json.loads(await Fetch(json_data))
            response = response_json["choices"][0]["message"]["content"]
            FM.Log(response)

            # Find summary text
            result = re.search(r".*Summary.*?([a-zA-Z0-9_']+[a-zA-Z0-9_' ]+)", response)
            thread_name = result.group(1)[:15]

            # Construct the body of the response (without summary)
            response_body = ""
            for line in response.splitlines():
                if "Summary" not in line:
                    response_body += f"\n{line}"

            # Create a thread to house the conversation
            thread = await interaction.channel.create_thread(
                name = thread_name,
                type = discord.ChannelType.public_thread,
                message = None
            )

            # Notify the user that a new thread has been created to house this chat
            await interaction.followup.send(content = f"I've created a thread for us!\n{thread.mention}")

            # Send the thread details and the response body
            await thread.send(content=f"**Personality**\n`{personality}`\n**Message**\n`{message}`\n\n{response_body.strip()}")

            while True:
                # Reset personality to remove summary
                json_data["messages"][0]['content'] = f"{personality} - formatted nicely"

                # Append assistant's message
                json_data["messages"].append({
                    'role': 'assistant',
                    'content': response_body,
                })

                # Wait for a reply in accordance with the check function
                msg: discord.Message = await self.bot.wait_for('message', check = lambda m: m.channel.id == thread.id)#, timeout=10.0)

                # End the conversation if the msg is empty
                if msg is None:
                    FM.Log("Thanks for chatting!")
                    await thread.send("Thanks for chatting!")
                    break

                # Append user's message
                json_data["messages"].append({
                    'role': 'user',
                    'content': f"{msg.content} - limit your response to a maximum of 1000 characters",
                })
                
                FM.Log(json.dumps(json_data["messages"], indent=2))

                # Fetch a new response
                response_json = json.loads(await Fetch(json_data))
                response_body = response_json["choices"][0]["message"]["content"]
                FM.Log(response)

                # Reply with a response
                await msg.reply(content=f"\n{response_body}")

        except Exception as e:
            FM.Log(str(e), LogType.Error)
            raise e