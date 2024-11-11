
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
                    'content': f"{personality}. Answer in this format:\n**Summary:** *[summary that's 15 characters or less]*\n\n[formatted body of response] ",
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
            result = re.search(r".*Summary.*?([a-zA-Z0-9_].*)\*", response)
            thread_name = result.group(1)[:15]

            # Construct the body of the response (without summary)
            response_body = ""
            for line in response.splitlines():
                if "Summary" not in line:
                    response_body += f"\n{line}"

            # Create a thread to house the conversation
            thread = await interaction.channel.create_thread(
                name = thread_name,
                type = discord.ChannelType.private_thread
            )

            # Notify the user that a new thread has been created to house this chat
            await interaction.followup.send(content = f"I've created a thread for us!\n{thread.mention}")

            # Send the thread details and the response body
            await thread.send(content=f"**Personality**\n*{personality}*\n**Message**\n*{message}*")
            original_message = await thread.send(content=f"\n{response_body}")

            message_id = original_message.id
            while True:
                # Returns true of the message is a reply to the original message
                def check(message):
                    return message.reference and message.reference.message_id == message_id

                # Reset personality to remove summary
                json_data["messages"][0]['content'] = f"{personality} - formatted nicely"

                # Append assistant's message
                json_data["messages"].append({
                    'role': 'assistant',
                    'content': response_body,
                })

                # Wait for a reply in accordance with the check function
                msg: discord.Message = await self.bot.wait_for('message', check = check)#, timeout=10.0)

                # End the conversation if the msg is empty
                if msg is None:
                    FM.Log("Thanks for chatting!")
                    await thread.send("Thanks for chatting!")
                    break

                # Append user's message
                json_data["messages"].append({
                    'role': 'user',
                    'content': msg.content,
                })

                # Fetch a new response
                response_json = json.loads(await Fetch(json_data))
                response = response_json["choices"][0]["message"]["content"]
                FM.Log(response)

                # Reply with a response
                new_message = await thread.send(content=f"\n{response}")
                message_id = new_message.id

        except Exception as e:
            FM.Log(str(e), LogType.Error)