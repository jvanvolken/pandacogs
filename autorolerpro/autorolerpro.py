# Discord Bot Libraries
import discord
import json
import os
from redbot.core import commands

# Initializes intents
intents = discord.Intents(messages=True, guilds=True)
intents.members = True

# Initializes client with intents
client = discord.Client(intents = intents)

# Cog Directory in Appdata
docker_cog_path = "/data/cogs/AutoRoler"
games_list_file = f"{docker_cog_path}/games.txt"

# Create the docker_cog_path if it doesn't already exist
os.makedirs(docker_cog_path, exist_ok = True)

# Initialize the games list
if os.path.isfile(games_list_file):
    with open(games_list_file, "r") as fp:
        games = json.load(fp)
else:
    games = []
    with open(games_list_file, "w") as fp:
        json.dump(games, fp)

# List of games
# games = ["Overwatch", "Project Zomboid", "Tabletop Simulator", "Golf With Your Friends", "Rocket League", "PlateUp!", "Lethal Company", "Apex Legends"]

 # Create a class called GameListView that subclasses discord.ui.View
class GameListView(discord.ui.View):
    def __init__(self):
        super().__init__()

        for game in games:
            self.add_item(self.GameButton(game))
    
    # Create a class called GameButton that subclasses discord.ui.Button
    class GameButton(discord.ui.Button):
        def __init__(self, name):
            super().__init__(label = name, style=discord.ButtonStyle.primary, emoji = "😎")
            self.name = name

        async def callback(self, interaction):
            await interaction.response.send_message(f"You selected {self.name}!")


class AutoRolerPro(commands.Cog):
    """My custom cog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def list_games(self, ctx):
        """Lists the collected game roles for the server."""
        if len(games) > 0:
            await ctx.reply("Please select the games that you're interested in playing!", view = GameListView()) # Send a message with our View class that contains the button
        else:
            await ctx.reply("This is where I would list my games... IF I HAD ANY!")
        
    @commands.command()
    async def add_game(self, ctx, arg):
        games.append(arg)
        with open(games_list_file, "w") as fp:
            json.dump(games, fp)

        await ctx.reply(f"Thanks for the contribution! Added {arg} to the list of games!")

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