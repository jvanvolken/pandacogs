# Discord Bot Libraries
import difflib
import discord
import json
import os
import string
from discord.utils import get
from operator import itemgetter
from redbot.core import commands
from requests import post
from datetime import datetime

from enum import Enum

# Initializes intents
intents = discord.Intents(messages=True, guilds=True)
intents.members = True

# Initializes client with intents
client = discord.Client(intents = intents)

# Cog Directory in Appdata
docker_cog_path = "/data/cogs/AutoRoler"
games_list_file = f"{docker_cog_path}/games.json"

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
    games = {}
    with open(games_list_file, "w") as fp:
        json.dump(games, fp)

# Adds game to games list and saves to file
def AddGame(game):
    games[game['name']] = game
    with open(games_list_file, "w") as fp:
        json.dump(games, fp)

# Removes game to games list and saves to file
def RemoveGame(game):
    if game['name'] in games:
        del games[game['name']]
        with open(games_list_file, "w") as fp:
            json.dump(games, fp)
    else:
        print(f"Failed to remove game. Could not find {game['name']} in list.")

# Returns a string list of game names
def GetNames(game_list):
    names = []
    for game in game_list.values():
        names.append(game['name'])
    return (', '.join(names))

 # Create a class called GameListView that subclasses discord.ui.View
class GameListView(discord.ui.View):
    def __init__(self, ctx, list_type, game_list):
        super().__init__()
        self.ctx = ctx
        self.list_type = list_type
        self.game_list = game_list

        for game in self.game_list.values():
            self.add_item(self.GameButton(self.ctx, game, self.list_type))
    
    # Create a class called GameButton that subclasses discord.ui.Button
    class GameButton(discord.ui.Button):
        def __init__(self, ctx, game, list_type):
            super().__init__(label = game['name'], style=discord.ButtonStyle.primary, emoji = "😎")
            self.ctx = ctx
            self.game = game
            self.list_type = list_type

        async def callback(self, interaction):
            if self.list_type is ListType.Select:
                # await interaction.response.send_message(f"You have selected {self.game['name']}!")
                if get(self.ctx.guild.roles, name=self.game['name']):
                    await self.ctx.send(f"Added you to the {self.game['name']} role!")
                else:                            
                    db_json = post('https://api.igdb.com/v4/covers', **{'headers' : db_header, 'data' : f'fields url; limit 1; where animated = "false"; where game = {self.game["cover"]};'})
                    results = db_json.json()
                    print(results)
                    await self.ctx.send(f"{results[0]['url']}")
                    # await self.ctx.guild.create_role(name=self.game['name'], colour=discord.Colour(0x0062ff))

            elif self.list_type is ListType.Remove:
                RemoveGame(self.game)
                await interaction.response.edit_message(content = "Please select the game(s) you'd like to remove...", view = GameListView(self.ctx, ListType.Remove, games))
                await interaction.followup.send(f"I have removed {self.game['name']} from the list!")


class AutoRolerPro(commands.Cog):
    """My custom cog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def list_games(self, ctx):
        """Lists the collected game roles for the server."""
        if len(games) > 0:
            await ctx.reply("Please select the games that you're interested in playing!", view = GameListView(ctx, ListType.Select, games)) # Send a message with our View class that contains the button
        else:
            await ctx.reply("This is where I would list my games... IF I HAD ANY!")
        
    @commands.command()
    async def add_games(self, ctx, *, arg):
        """Manually adds a game or a set of games to the autoroler.\nSeperate games using commas: !add_games game_1, game_2, ..., game_n"""
        all_games = [string.capwords(game) for game in arg.split(',')]

        already_exists = {}
        failed_to_find = {}
        new_games      = {}
        for game in all_games:
            # Get games with the provided name
            db_json = post('https://api.igdb.com/v4/games', **{'headers' : db_header, 'data' : f'search "{game}"; fields name,summary,rating,first_release_date,cover; limit 500; where summary != null; where rating != null;'})
            results = db_json.json()

            # Collect the game names
            game_names = [details['name'] for details in results]

            # Get the top match for the provided name
            matches = difflib.get_close_matches(game, game_names, 1)

            latest_game = None
            for game in results:
                if latest_game and game['name'] in matches:
                    latest_year = datetime.utcfromtimestamp(latest_game['first_release_date']).strftime('%Y')
                    release_year = datetime.utcfromtimestamp(game['first_release_date']).strftime('%Y')
                    if release_year > latest_year:
                        latest_game = game
                elif game['name'] in matches:
                    latest_game = game

            
            if latest_game and latest_game['name'] in games:
                already_exists[latest_game['name']] = latest_game
            elif latest_game: 
                AddGame(latest_game)
                new_games[latest_game['name']] = latest_game
            else:
                failed_to_find[game] = {'name' : game, 'summary' : 'unknown', 'rating' : 0, 'first_release_date' : 'unknown'}

        if len(new_games) == 0 and len(already_exists) == 0 and len(failed_to_find) == 0:
            await ctx.reply(f"You need to actually tell me what you want to add")
        elif len(new_games) == 0 and len(already_exists) == 0 and len(failed_to_find) > 0:
            await ctx.reply(f"I don't recognize any of these games. Are you sure you know what you're talking about?")
        elif len(new_games) == 0 and len(already_exists) > 0 and len(failed_to_find) == 0:
            await ctx.reply(f"I already have all of these recorded! How about you do a little research before asking questions.", view = GameListView(ctx, ListType.Select, already_exists))
        elif len(new_games) == 0 and len(already_exists) > 0 and len(failed_to_find) > 0:
            await ctx.reply(f"Thanks for the contribution! I already have {GetNames(already_exists)}, but I don't recognize {GetNames(failed_to_find)}.", view = GameListView(ctx, ListType.Select, already_exists))
        elif len(new_games) > 0 and len(already_exists) == 0 and len(failed_to_find) == 0:
            await ctx.reply(f"Thanks for the contribution! I've added {GetNames(new_games)} to the list of games!", view = GameListView(ctx, ListType.Select, new_games))
        elif len(new_games) > 0 and len(already_exists) == 0 and len(failed_to_find) > 0:
            await ctx.reply(f"Thanks for the contribution! I've added {GetNames(new_games)} to the list of games! But I don't recognize {GetNames(failed_to_find)}.", view = GameListView(ctx, ListType.Select, new_games))
        elif len(new_games) > 0 and len(already_exists) > 0 and len(failed_to_find) == 0:
            await ctx.reply(f"Thanks for the contribution! I've added {GetNames(new_games)} to the list of games! I already have {GetNames(already_exists)}.", view = GameListView(ctx, ListType.Select, new_games + already_exists))
        elif len(new_games) > 0 and len(already_exists) > 0 and len(failed_to_find) > 0:
            await ctx.reply(f"Thanks for the contribution! I've added {GetNames(new_games)} to the list of games! I already have {GetNames(already_exists)}, but I don't recognize {GetNames(failed_to_find)}.", view = GameListView(ctx, ListType.Select, new_games + already_exists))


    @commands.command()
    async def remove_games(self, ctx):
        """Lists the collected games to select for removal."""
        if len(games) > 0:
            await ctx.reply("Please select the game(s) you'd like to remove...", view = GameListView(ctx, ListType.Remove, games)) # Send a message with our View class that contains the button
        else:
            await ctx.reply("This is where I would list my games... IF I HAD ANY!")

    @commands.command()
    async def search_game(self, ctx, *, arg):
        """Searches IGDB for a matching game."""
        db_json = post('https://api.igdb.com/v4/games', **{'headers' : db_header, 'data' : f'search "{arg}"; fields name,summary,rating,first_release_date; limit 500; where summary != null; where rating != null;'})
        results = db_json.json()

        if len(results) > 0:
            # Sort the results by rating
            results = sorted(results, key=itemgetter('rating'), reverse=True)

            # Get the result names and get the top 3 matches
            game_names = [details['name'] for details in results]
            matches = difflib.get_close_matches(arg, game_names, 3)

            # Construct the reply
            reply = "## Here are the results!\n"
            for details in results:
                try:
                    if details['name'] in matches:
                        reply += f"  [*({round(details['rating'], 2)}) {details['name']}* ({datetime.utcfromtimestamp(details['first_release_date']).strftime('%Y')})](<https://www.igdb.com/games/{details['name'].lower().replace(' ', '-')}>)\n"
                except:
                    reply += str(details)

            await ctx.reply(reply[:2000])
        else:
            await ctx.reply(f"Sorry! No results found for {arg}.")


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