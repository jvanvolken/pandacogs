# Discord Bot Libraries
import difflib
import io
import discord
import json
import os
import string
import requests
from PIL import Image
from io import BytesIO
from operator import itemgetter
from redbot.core import commands
from datetime import datetime
from enum import Enum

# Initializes intents
intents = discord.Intents(messages=True, guilds=True)
intents.members = True

# Initializes client with intents
client = discord.Client(intents = intents)

# Cog Directory in Appdata
docker_cog_path  = "/data/cogs/AutoRoler"
games_list_file  = f"{docker_cog_path}/games.json"
temp_cover_image = f"{docker_cog_path}/temp_cover.png"

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
    return f"`{'`, `'.join(names)}`"

# Returns a string list of game names
async def GetImages(game_list):
    images = []
    for game in game_list.values():
        response = requests.get(game['cover_url'])
        img = Image.open(BytesIO(response.content))

        # Construct safe filename from game name
        filename = "".join(c for c in game['name'] if c.isalpha() or c.isdigit() or c == ' ').rstrip()

        # Convert PIL image to a useable binary image
        with io.BytesIO() as image_binary:
            img.save(image_binary, 'PNG')
            image_binary.seek(0)
            images.append(discord.File(fp=image_binary, filename=f"{filename}_cover.png"))

    return images

# Returns the dominant color of an image
def GetDominantColor(image_url, palette_size=16):
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))

    # Resize image to speed up processing
    img.thumbnail((100, 100))

    # Reduce colors (uses k-means internally)
    paletted = img.convert('P', palette=Image.Palette.ADAPTIVE, colors=palette_size)

    # Find the color that occurs most often
    palette = paletted.getpalette()
    color_counts = sorted(paletted.getcolors(), reverse=True)
    palette_index = color_counts[0][1]
    dominant_color = palette[palette_index*3:palette_index*3+3]

    return ('%02X%02X%02X' % tuple(dominant_color))

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
        async def __init__(self, ctx, game, list_type):
            # emoji = await ctx.guild.fetch_emoji(game['name'].lower())

            super().__init__(label = game['name'], style=discord.ButtonStyle.primary, emoji = ":)")
            self.ctx = ctx
            self.game = game
            self.list_type = list_type

        async def callback(self, interaction):
            if self.list_type is ListType.Select:
                # Looks for the role with the same name as the game
                role = discord.utils.get(self.ctx.guild.roles, name=self.game['name'])
                if role:
                    # Assign role to member
                    member = interaction.user
                    await member.add_roles(role)

                    # Informs the user that the role has been assigned to them
                    await interaction.response.send_message(f"Added you to the `{self.game['name']}` role!")
                else:
                    await interaction.response.send_message(f"Something went wrong, I can't find the associated role for `{self.game['name']}`.\nPlease try adding the game again using !add_games {self.game['name']}")

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
        # List the games if there are more than zero. Otherwise reply with a passive agressive comment
        if len(games) > 0:
            await ctx.reply(f"Here's your game list, {ctx.message.author.mention}!\n*Please select the games that you're interested in playing:*", view = GameListView(ctx, ListType.Select, games))
        else:
            await ctx.reply("This is where I would list my games... IF I HAD ANY!")
        
    @commands.command()
    async def add_games(self, ctx, *, arg):
        """Manually adds a game or a set of games to the autoroler.\nSeperate games using commas: !add_games game_1, game_2, ..., game_n"""
        # Splits the provided arg into a list of games
        all_games = [string.capwords(game) for game in arg.split(',')]

        already_exists = {}
        failed_to_find = {}
        new_games      = {}
        for game in all_games:
            # Get games with the provided name
            db_json = requests.post('https://api.igdb.com/v4/games', **{'headers' : db_header, 'data' : f'search "{game}"; fields name,summary,rating,first_release_date; limit 500; where summary != null; where rating != null;'})
            results = db_json.json()

            # Collect the game names
            game_names = [details['name'] for details in results]

            # Get the top match for the provided name
            matches = difflib.get_close_matches(game, game_names, 1)

            # Compares the list of games to the matches, from there sort by release year
            latest_game = None
            for game_details in results:
                if latest_game and game_details['name'] in matches:
                    latest_year = datetime.utcfromtimestamp(latest_game['first_release_date']).strftime('%Y')
                    release_year = datetime.utcfromtimestamp(game_details['first_release_date']).strftime('%Y')
                    if release_year > latest_year:
                        latest_game = game_details
                elif game_details['name'] in matches:
                    latest_game = game_details

            # Sort the games by alreadying existing, new games, and failed to find
            if latest_game and latest_game['name'] in games:
                already_exists[latest_game['name']] = latest_game
            elif latest_game: 
                new_games[latest_game['name']] = latest_game
                AddGame(latest_game)

                # Request the cover image urls
                db_json = requests.post('https://api.igdb.com/v4/covers', **{'headers' : db_header, 'data' : f'fields url; limit 1; where animated = false; where game = {latest_game["id"]};'})
                results = db_json.json()

                # Formats the cover URL
                url = f"https:{results[0]['url']}"
                url = url.replace("t_thumb", "t_cover_big")

                # Stores the formatted URL in the latest game dictionary
                latest_game['cover_url'] = url
                
                # Create the Role and give it the dominant color of the cover art
                color = GetDominantColor(url)
                
                role = discord.utils.get(ctx.guild.roles, name = latest_game['name'])
                if role:
                    await role.edit(colour = discord.Colour(int(color, 16)))
                else:
                    await ctx.guild.create_role(name = latest_game['name'], colour = discord.Colour(int(color, 16)), mentionable = True)
            else:
                failed_to_find[game] = {'name' : game, 'summary' : 'unknown', 'rating' : 0, 'first_release_date' : 'unknown'}

        # Respond in one of the 8 unique ways based on the types of games trying to be added
        if len(new_games) == 0 and len(already_exists) == 0 and len(failed_to_find) == 0:
            await ctx.reply(f"You need to actually tell me what you want to add")
        elif len(new_games) == 0 and len(already_exists) == 0 and len(failed_to_find) > 0:
            await ctx.reply(f"I don't recognize any of these games. Are you sure you know what you're talking about?")
        elif len(new_games) == 0 and len(already_exists) > 0 and len(failed_to_find) == 0:
            await ctx.reply(f"I already have all of these recorded! How about you do a little research before asking questions.", 
                            view = GameListView(ctx, ListType.Select, already_exists))
        elif len(new_games) == 0 and len(already_exists) > 0 and len(failed_to_find) > 0:
            await ctx.reply(f"Thanks for the contribution! I already have {GetNames(already_exists)}, but I don't recognize {GetNames(failed_to_find)}.", 
                            view = GameListView(ctx, ListType.Select, already_exists))
        elif len(new_games) > 0 and len(already_exists) == 0 and len(failed_to_find) == 0:
            await ctx.reply(f"Thanks for the contribution! I've added {GetNames(new_games)} to the list of games!", 
                            view = GameListView(ctx, ListType.Select, new_games), files = await GetImages(new_games))
        elif len(new_games) > 0 and len(already_exists) == 0 and len(failed_to_find) > 0:
            await ctx.reply(f"Thanks for the contribution! I've added {GetNames(new_games)} to the list of games! But I don't recognize {GetNames(failed_to_find)}.", 
                            view = GameListView(ctx, ListType.Select, new_games), files = await GetImages(new_games))
        elif len(new_games) > 0 and len(already_exists) > 0 and len(failed_to_find) == 0:
            await ctx.reply(f"Thanks for the contribution! I've added {GetNames(new_games)} to the list of games! I already have {GetNames(already_exists)}.", 
                            view = GameListView(ctx, ListType.Select, new_games | already_exists), files = await GetImages(new_games))
        elif len(new_games) > 0 and len(already_exists) > 0 and len(failed_to_find) > 0:
            await ctx.reply(f"Thanks for the contribution! I've added {GetNames(new_games)} to the list of games! I already have {GetNames(already_exists)}, but I don't recognize {GetNames(failed_to_find)}.", 
                            view = GameListView(ctx, ListType.Select, new_games | already_exists), files = await GetImages(new_games))

    @commands.command()
    async def remove_games(self, ctx):
        """Lists the collected games to select for removal."""
        # Lists the games to remove if there's more than zero. Otherwise reply with a passive agressive comment
        if len(games) > 0:
            await ctx.reply("Please select the game(s) you'd like to remove...", view = GameListView(ctx, ListType.Remove, games)) # Send a message with our View class that contains the button
        else:
            await ctx.reply("This is where I would list my games... IF I HAD ANY!")

    @commands.command()
    async def search_game(self, ctx, *, arg):
        """Searches IGDB for a matching game."""
        # Returns a list of games that fit the provided name
        db_json = requests.post('https://api.igdb.com/v4/games', **{'headers' : db_header, 'data' : f'search "{arg}"; fields name,summary,rating,first_release_date; limit 500; where summary != null; where rating != null;'})
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

    @commands.command()
    async def test_emojis(self, ctx, *, arg):
        emojis = ctx.guild.emojis

        emoji_names = [emoji.name for emoji in emojis]
        match = difflib.get_close_matches(arg, emoji_names, 1)

        emoji = None
        if match:
            for option in emojis:
                if option.name == match[0]:
                    emoji = option
                    break
        
        await ctx.reply(f"Here is the closest emoji! {emoji}.")


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