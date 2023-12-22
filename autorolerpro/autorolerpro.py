# Discord Bot Libraries
import discord
import json
import os
import string
from redbot.core import commands
from requests import post

from enum import Enum

# Initializes intents
intents = discord.Intents(messages=True, guilds=True)
intents.members = True

# Initializes client with intents
client = discord.Client(intents = intents)

# Cog Directory in Appdata
docker_cog_path = "/data/cogs/AutoRoler"
games_list_file = f"{docker_cog_path}/games.txt"

# Instantiates IGDB wrapper
# curl -X POST "https://id.twitch.tv/oauth2/token?client_id=CLIENT_ID&client_secret=CLIENT_SECRET&grant_type=client_credentials"
db_header = {
    'Client-ID': 'fqwgh1wot9cg7nqu8wsfuzw01lsln9',
    'Authorization': 'Bearer 9csdv9i9a61vpschjcdcsfm4nblpyq'
}

# Game list functions
class ListType(Enum):
    Select = 1
    Remove = 2

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

# Adds game to games list and saves to file
def AddGame(game):
    games.append(game)
    with open(games_list_file, "w") as fp:
        json.dump(games, fp)

# Removes game to games list and saves to file
def RemoveGame(game):
    if game in games:
        games.remove(game)
        with open(games_list_file, "w") as fp:
            json.dump(games, fp)
    else:
        print(f"Failed to remove game. Could not find {game} in list.")

 # Create a class called GameListView that subclasses discord.ui.View
class GameListView(discord.ui.View):
    def __init__(self, list_type, game_list):
        super().__init__()
        self.list_type = list_type
        self.game_list = game_list

        for game in self.game_list:
            self.add_item(self.GameButton(game, self.list_type))
    
    # Create a class called GameButton that subclasses discord.ui.Button
    class GameButton(discord.ui.Button):
        def __init__(self, name, list_type):
            super().__init__(label = name, style=discord.ButtonStyle.primary, emoji = "😎")
            self.name = name
            self.list_type = list_type

        async def callback(self, interaction):
            if self.list_type is ListType.Select:
                await interaction.response.send_message(f"You have selected {self.name}!")
            elif self.list_type is ListType.Remove:
                RemoveGame(self.name)
                await interaction.response.edit_message(content = "Please select the game(s) you'd like to remove...", view = GameListView(ListType.Remove, games))
                await interaction.followup.send(f"I have removed {self.name} from the list!")


class AutoRolerPro(commands.Cog):
    """My custom cog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def list_games(self, ctx):
        """Lists the collected game roles for the server."""
        if len(games) > 0:
            await ctx.reply("Please select the games that you're interested in playing!", view = GameListView(ListType.Select, games)) # Send a message with our View class that contains the button
        else:
            await ctx.reply("This is where I would list my games... IF I HAD ANY!")
        
    @commands.command()
    async def add_games(self, ctx, *, arg):
        """Manually adds a game or a set of games to the autoroler.\nSeperate games using commas: !add_games game_1, game_2, ..., game_n"""
        new_games = [string.capwords(game) for game in arg.split(',')]
        already_exists = []
        for game in new_games:
            if game in games:
                already_exists.append(game)
            else:   
                AddGame(game)
        
        for game in already_exists:
            new_games.remove(game)

        if len(already_exists) > 0:
            if len(new_games) > 0:
                await ctx.reply(f"Thanks for the contribution! I've added {', '.join(new_games)} to the list of games! I already have {', '.join(already_exists)}.", view = GameListView(ListType.Select, new_games + already_exists))
            else:
                await ctx.reply(f"Thanks for the contribution! But I already have these!", view = GameListView(ListType.Select, already_exists))
        else:
            await ctx.reply(f"Thanks for the contribution! Added {', '.join(new_games)} to the list of games!", view = GameListView(ListType.Select, new_games))

    @commands.command()
    async def remove_games(self, ctx):
        """Lists the collected games to select for removal."""
        if len(games) > 0:
            await ctx.reply("Please select the game(s) you'd like to remove...", view = GameListView(ListType.Remove, games)) # Send a message with our View class that contains the button
        else:
            await ctx.reply("This is where I would list my games... IF I HAD ANY!")

    @commands.command()
    async def search_game(self, ctx, *, arg):
        """Searches IGDB for a matching game."""
        db_json = post('https://api.igdb.com/v4/search', **{'headers' : db_header, 'data' : f'search "{arg}"; fields *;'})

        
        reply = "Here are the results!\n"
        for details in db_json.json():
            reply += f"**{details['name']}**\n"

        await ctx.reply(reply)

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