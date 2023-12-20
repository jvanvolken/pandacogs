# Discord Bot Libraries
import discord
from redbot.core import commands

# Initializes intents
intents = discord.Intents(messages=True, guilds=True)
intents.members = True

# Initializes client with intents
client = discord.Client(intents = intents)

# Cog Directory in Appdata
docker_cog_path = "/data/cogs/AutoRoler"

# List of games


class MyView(discord.ui.View): # Create a class called MyView that subclasses discord.ui.View
    @discord.ui.button(label="Click me!", style=discord.ButtonStyle.primary, emoji="😎") # Create a button with the label "😎 Click me!" with color Blurple
    async def button_callback(self, interaction, button):
        await interaction.response.send_message("You're the best!") # Send a message when the button is clicked

    @discord.ui.button(label="No me!", style=discord.ButtonStyle.primary, emoji="😎") # Create a button with the label "😎 Click me!" with color Blurple
    async def button_callback(self, interaction, button):
        await interaction.response.send_message("Thanks bud!") # Send a message when the button is clicked

    @discord.ui.button(label="uWu!", style=discord.ButtonStyle.primary, emoji="😎") # Create a button with the label "😎 Click me!" with color Blurple
    async def button_callback(self, interaction, button):
        await interaction.response.send_message("Hi daddy!") # Send a message when the button is clicked

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
        # await channel.send(f"This is where I'd list the games... If I had any!!")

        await ctx.reply("This is a button!", view = MyView()) # Send a message with our View class that contains the button


    @client.event
    async def on_member_update(self, previous, current):

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