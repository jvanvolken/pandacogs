# Discord Bot Libraries
import difflib
import io
import math
import discord
import json
import os
import string
import requests
from PIL import Image
from io import BytesIO
from redbot.core import commands
from datetime import datetime
from enum import Enum

# Initializes intents
intents = discord.Intents(messages=True, guilds=True, members = True, presences = True)

# Initializes client with intents
client = discord.Client(intents = intents)

# Cog Directory in Appdata
docker_cog_path = "/data/cogs/AutoRoler"
games_file   = f"{docker_cog_path}/games.json"
members_file = f"{docker_cog_path}/members.json"

# Channel Links
general_channel_link = "https://discord.com/channels/633799810700410880/633799810700410882"

# Blacklist for member activities
activity_blacklist = ["Spotify"]

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

# Initializes the games list
if os.path.isfile(games_file):
    with open(games_file, "r") as fp:
        games = json.load(fp)
else:
    games = {}
    with open(games_file, "w") as fp:
        json.dump(games, fp, indent = 2, default = str)

# Initializes the members list
if os.path.isfile(members_file):
    with open(members_file, "r") as fp:
        members = json.load(fp)
else:
    members = {}
    with open(members_file, "w") as fp:
        json.dump(members, fp, indent = 2, default = str)

# Removes game from games list and saves to file
def RemoveGame(game):
    if game['name'] in games:
        del games[game['name']]
        with open(games_file, "w") as fp:
            json.dump(games, fp, indent = 2, default = str)
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

# Return a list of game sets containing a max of 25 games per set
def GetGameSets(game_list):
    message_sets = []
    game_count = 0
    for game in game_list.values():
        idx = math.floor(game_count/25)
        if idx < len(message_sets):
            message_sets[idx][game['name']] = game
        else:
            message_sets.append({})
            message_sets[idx][game['name']] = game
        game_count += 1

    return message_sets

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

# Adds a member to the members list and saves file
def AddMember(member):
    # Collects the desired information about the member
    member_details = {}
    for detail in ['name', 'display_name', 'created_at', 'joined_at', 'roles']:
        if hasattr(member, detail):
            member_details[detail] = getattr(member, detail)

    member_details['games'] = {}
    member_details['opt_out'] = False
    
    # Adds the member details to the members list
    members[member_details['name']] = member_details

    # Saves the members dictionary to the json file
    with open(members_file, "w") as fp:
        json.dump(members, fp, indent = 2, default = str)

    # Update first dict with second recursively
def MergeDictionaries(d1, d2):
    for k, v in d1.items():
        if k in d2:
            d2[k] = MergeDictionaries(v, d2[k])
    d1.update(d2)
    return d1

# Updates a member to the members list and saves file
def UpdateMember(member_name, new_details):
    # Updates specific member with new details
    MergeDictionaries(members[member_name], new_details)
        
    # Saves the members dictionary to the json file
    with open(members_file, "w") as fp:
        json.dump(members, fp, indent = 2, default = str)

# Adds a list of games to the games list after verifying they are real games
async def AddGames(server, game_list):
    new_games      = {}
    already_exists = {}
    failed_to_find = {}
    for game in game_list:
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

            # Add game to game list and saves file
            games[latest_game['name']] = latest_game
            with open(games_file, "w") as fp:
                json.dump(games, fp, indent = 2, default = str)

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
            
            role = discord.utils.get(server.roles, name = latest_game['name'])
            if role:
                await role.edit(colour = discord.Colour(int(color, 16)))
            else:
                await server.create_role(name = latest_game['name'], colour = discord.Colour(int(color, 16)), mentionable = True)
        else:
            failed_to_find[game] = {'name' : game, 'summary' : 'unknown', 'rating' : 0, 'first_release_date' : 'unknown'}
        
    return new_games, already_exists, failed_to_find

# Create a class called DirectMessageView that subclasses discord.ui.View
class DirectMessageView(discord.ui.View):
    def __init__(self, original_message, role, member):
        super().__init__(timeout = 60)

        self.original_message = original_message
        self.role = role
        self.member = member

        self.add_item(self.YesButton(self.original_message, self.role, self.member))
        self.add_item(self.NoButton(self.original_message, self.role, self.member))
        self.add_item(self.OptOutButton(self.original_message, self.role, self.member))

    # Create a class called GameButton that subclasses discord.ui.Button
    class YesButton(discord.ui.Button):
        def __init__(self, original_message, role, member):
            super().__init__(label = "YES", style = discord.ButtonStyle.success, emoji = "😀")
            self.original_message = original_message
            self.role = role
            self.member = member

        async def callback(self, interaction):
            try:
                # Assign role to member
                await self.member.add_roles(self.role)
                
                # Records answer for this game and the current datetime for last played
                update = {'games' : {self.role.name : {'name' : self.role.name, 'tracked' : True, 'last_played' : datetime.now()}}}
                UpdateMember(self.member.name, update)

                # Responds to the request
                await interaction.message.edit(content = f"{self.original_message}\n*You've selected `YES`*", view = None)
                await interaction.response.send_message(f"Awesome! I've added you to the `{self.role.name}` role! Go ahead and mention the role in the [server]({general_channel_link}) to meet some new friends!")
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, something went wrong! I was unable to assign the `{self.role.name}` role to you. Please check the logs for further details.")
                raise Exception(error)
                             
    class NoButton(discord.ui.Button):
        def __init__(self, original_message, role, member):
            super().__init__(label = "NO", style = discord.ButtonStyle.secondary, emoji = "😕")
            self.original_message = original_message
            self.role = role
            self.member = member

        async def callback(self, interaction):
            try:
                # Remove role from member if exists
                if self.role in self.member.roles:
                    await self.member.remove_roles(self.role)

                # Records answer for this game and the current datetime for last played
                update = {'games' : {self.role.name : {'name' : self.role.name, 'tracked' : False, 'last_played' : None}}}
                UpdateMember(self.member.name, update)
                
                await interaction.message.edit(content = f"{self.original_message}\n*You've selected `NO`*", view = None)
                await interaction.response.send_message(f"Understood! I won't ask about `{self.role.name}` again! Feel free to manually add yourself anytime using the !list_games command in the [server]({general_channel_link})!")
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, I was unable to complete the requested command! Please check the logs for further details.")
                raise Exception(error)
                             
    class OptOutButton(discord.ui.Button):
        def __init__(self, original_message, role, member):
            super().__init__(label = "OPT OUT", style = discord.ButtonStyle.danger, emoji = "😭")
            self.original_message = original_message
            self.role = role
            self.member = member

        async def callback(self, interaction):
            try:
                # Updates the out_out flag for the member
                update = {'opt_out' : True}
                UpdateMember(self.member.name, update)

                await interaction.message.edit(content = f"{self.original_message}\n*You've selected `OPT OUT`*", view = None)
                await interaction.response.send_message(f"Sorry to bother! I've opted you out of the automatic role assignment! If in the future you'd like to opt back in, simply use the !opt_in command anywhere in the [server]({general_channel_link})!")
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, I was unable to complete the requested command! Please check the logs for further details.")
                raise Exception(error)

    async def on_timeout(self):
        #TODO Make this edit dynamic based on what the user selected (or didn't)
        await self.message.edit(content = f"{self.original_message}\n*This request has timed out but you can still add youself to the roll by using the command `!list_games` in the [server]({general_channel_link})!*", view = None)

# Create a class called GameListView that subclasses discord.ui.View
class GameListView(discord.ui.View):
    def __init__(self, ctx, list_type, game_list):
        super().__init__()
        self.ctx = ctx
        self.list_type = list_type
        self.game_list = game_list

        for game in self.game_list.values():
            self.add_item(self.GameButton(self.ctx, game, self.list_type, self.game_list))
    
    # Create a class called GameButton that subclasses discord.ui.Button
    class GameButton(discord.ui.Button):
        def __init__(self, ctx, game, list_type, game_list):
            # Get all server emojis
            emojis = ctx.guild.emojis

            # Get the closest matching emoji to game name
            emoji_names = [emoji.name for emoji in emojis]
            match = difflib.get_close_matches(game['name'].lower(), emoji_names, 1)

            # Return the actual emoji from name
            emoji = None
            if match:
                for option in emojis:
                    if option.name == match[0]:
                        emoji = option
                        break
            
            # Set object variables
            self.ctx = ctx
            self.game = game
            self.list_type = list_type
            self.game_list = game_list
            self.role = discord.utils.get(self.ctx.guild.roles, name=self.game['name'])

            # Check if message author has the role and change button color accordingly
            if self.role in self.ctx.message.author.roles:
                button_style = discord.ButtonStyle.success
            else:
                button_style = discord.ButtonStyle.secondary

            # Setup buttom
            super().__init__(label = game['name'], style = button_style, emoji = emoji)

        async def callback(self, interaction):
            if self.ctx.message.author != interaction.user:
                extra_comment = ""
                if self.list_type is ListType.Select:
                    extra_comment = "Please use !list_games to interact!"
                    
                await interaction.response.send_message(f"You're not {self.ctx.message.author.mention}! Who are you?\n*{extra_comment}*", ephemeral = True)
                return
            
            if self.list_type is ListType.Select:
                # Looks for the role with the same name as the game
                if self.role:
                    if self.role in self.ctx.message.author.roles:
                        # Assign role to member
                        member = interaction.user
                        await member.remove_roles(self.role)
                        await interaction.message.edit(view = GameListView(self.ctx, ListType.Select, self.game_list))

                        await interaction.response.send_message(f"I have removed you from the `{self.game['name']}` role!", ephemeral = True)
                    else:
                        # Assign role to member
                        member = interaction.user
                        await member.add_roles(self.role)
                        await interaction.message.edit(view = GameListView(self.ctx, ListType.Select, self.game_list))

                        # Informs the user that the role has been assigned to them
                        await interaction.response.send_message(f"Added you to the `{self.game['name']}` role!", ephemeral = True)
                else:
                    await interaction.response.send_message(f"Something went wrong, I can't find the associated role for `{self.game['name']}`.\nPlease try adding the game again using !add_games {self.game['name']}", ephemeral = True)

            elif self.list_type is ListType.Remove:
                RemoveGame(self.game)
                del self.game_list[self.game['name']]
                await interaction.message.edit(view = GameListView(self.ctx, ListType.Remove, self.game_list))
                await interaction.response.send_message(f"I have removed {self.game['name']} from the list!", ephemeral = True)

class AutoRolerPro(commands.Cog):
    """My custom cog"""
    def __init__(self, bot):
        self.bot = bot

    # Detect when a member's presence changes
    @commands.Cog.listener(name='on_presence_update')
    async def on_presence_update(self, previous, current):
        # Get important information about the context of the event
        channel = current.guild.get_channel(665572348350693406)
        member_display_name = current.display_name.encode().decode('ascii','ignore')
        member_name = current.name

        # Exits if the member is a bot or isn't whitelisted
        if current.bot or member_name not in ["sad.panda.", "agvv20"]:
            return
        
        # Adds member to members dictionary for potential tracking (will ask if they want to opt-out)
        if member_name not in members:
            AddMember(current)

        member = members[member_name]
        # Exit if the member has opted out of the autoroler
        if member['opt_out']:
            return
        
        # Exits if there's a previous activity and it's the same as the current activity (prevents duplicate checks)
        if previous.activity and previous.activity.name == current.activity.name:
            return
        
        # Continues if there's a current activity and if it's not in the blacklist
        if current.activity and current.activity.name not in activity_blacklist:
            # Get list of game names
            game_names = []
            for game in games.values():
                game_names.append(game['name'])

            # If there isn't a game recorded for the current activity already, add it
            if current.activity.name not in game_names:
                new_games, already_exists, failed_to_find = await AddGames(current.guild, [current.activity.name])
                if len(new_games) > 0:
                    await channel.send(f"{member_display_name} starting playing a new game, `{current.activity.name}`! I've gone ahead and added it to the list.", files = await GetImages(new_games))
            
            # Get the role associated with the current activity name (game name)
            role = discord.utils.get(current.guild.roles, name = current.activity.name)

            # Exit if the member doesn't want to be bothered about this game
            if role.name in member['games'] and not member['games'][role.name]['tracked']:
                return 
            
            # When somebody starts playing a game and if they are part of the role
            if role in current.roles and role.name in member['games']: 
                await channel.send(f"{member_display_name} started playing {current.activity.name}!")
            else:
                # Informs the test channel that the member is playing a game without it's role assigned
                await channel.send(f"{member_display_name} started playing {current.activity.name} and does not have the role or is not being tracked!")

                # Get the direct message channel from the member
                dm_channel = await current.create_dm()

                # Setup original message
                original_message = f"Hey, {member_display_name}! I'm from the [Pavilion Horde server]({general_channel_link}) and I noticed you were playing `{current.activity.name}` but don't have the role assigned!"
                
                # Populate view and send direct message
                view = DirectMessageView(original_message, role, current)
                view.message = await dm_channel.send(f"{original_message} Would you like me to add you to it so you'll be notified when someone is looking for a friend?", view = view)
    
    @commands.command()
    async def opt_in(self, ctx, member):
        # Updates the out_out flag for the member
        update = {'opt_out' : False}
        UpdateMember(member, update)
        await ctx.reply(f"I've opted you back in for automatic role assignments! If in the future you'd like to opt back out, simply use the !opt_out command anywhere in the server!")

    @commands.command()
    async def opt_out(self, ctx, member):
        # Updates the out_out flag for the member
        update = {'opt_out' : True}
        UpdateMember(member, update)
        await ctx.reply(f"I've opted you out of the automatic role assignment! If in the future you'd like to opt back in, simply use the !opt_in command anywhere in the server!")

    @commands.command()
    async def list_games(self, ctx):
        """Lists the collected game roles for the server."""
        # List the games if there are more than zero. Otherwise reply with a passive agressive comment
        if len(games) > 0:
            # Convert a long list of games into sets of 25 or less
            message_sets = GetGameSets(games)

            # Loop through sets and send a message per
            set_count = 0
            while set_count < len(message_sets):
                if set_count == 0:
                    await ctx.reply(f"Here's your game list, {ctx.message.author.mention}!\n*Please select the games that you're interested in playing:*", view = GameListView(ctx, ListType.Select, message_sets[set_count]))
                else:
                    await ctx.reply(view = GameListView(ctx, ListType.Select, message_sets[set_count]))
                set_count += 1
        else:
            await ctx.reply("This is where I would list my games... IF I HAD ANY!")
        
    @commands.command()
    async def add_games(self, ctx, *, arg):
        """Manually adds a game or a set of games (max 10) to the autoroler.\nSeperate games using commas: !add_games game_1, game_2, ..., game_10"""
        # Splits the provided arg into a list of games
        all_games = [string.capwords(game) for game in arg.split(',')][:10]

        # Attempt to add the games provided, returning new, existing, and/or failed to add games
        new_games, already_exists, failed_to_find = await AddGames(ctx.guild, all_games)

        # Respond in one of the 8 unique ways based on the types of games trying to be added
        if len(new_games) == 0 and len(already_exists) == 0 and len(failed_to_find) == 0:
            await ctx.reply(f"{ctx.message.author.mention}, you need to actually tell me what you want to add")
        elif len(new_games) == 0 and len(already_exists) == 0 and len(failed_to_find) > 0:
            await ctx.reply(f"I don't recognize any of these games, {ctx.message.author.mention}. Are you sure you know what you're talking about?")
        elif len(new_games) == 0 and len(already_exists) > 0 and len(failed_to_find) == 0:
            await ctx.reply(f"I already have all of these recorded! {ctx.message.author.mention}, how about you do a little more research before asking questions.", 
                            view = GameListView(ctx, ListType.Select, already_exists))
        elif len(new_games) == 0 and len(already_exists) > 0 and len(failed_to_find) > 0:
            await ctx.reply(f"Thanks for the contribution, {ctx.message.author.mention}! I already have {GetNames(already_exists)}, but I don't recognize {GetNames(failed_to_find)}.", 
                            view = GameListView(ctx, ListType.Select, already_exists))
        elif len(new_games) > 0 and len(already_exists) == 0 and len(failed_to_find) == 0:
            await ctx.reply(f"Thanks for the contribution, {ctx.message.author.mention}! I've added {GetNames(new_games)} to the list of games!\n*Please select any of the games you're interested in playing below*", 
                            view = GameListView(ctx, ListType.Select, new_games), files = await GetImages(new_games))
        elif len(new_games) > 0 and len(already_exists) == 0 and len(failed_to_find) > 0:
            await ctx.reply(f"Thanks for the contribution, {ctx.message.author.mention}! I've added {GetNames(new_games)} to the list of games! But I don't recognize {GetNames(failed_to_find)}.\n*Please select any of the games you're interested in playing below*", 
                            view = GameListView(ctx, ListType.Select, new_games), files = await GetImages(new_games))
        elif len(new_games) > 0 and len(already_exists) > 0 and len(failed_to_find) == 0:
            await ctx.reply(f"Thanks for the contribution, {ctx.message.author.mention}! I've added {GetNames(new_games)} to the list of games! I already have {GetNames(already_exists)}.\n*Please select any of the games you're interested in playing below*", 
                            view = GameListView(ctx, ListType.Select, new_games | already_exists), files = await GetImages(new_games))
        elif len(new_games) > 0 and len(already_exists) > 0 and len(failed_to_find) > 0:
            await ctx.reply(f"Thanks for the contribution, {ctx.message.author.mention}! I've added {GetNames(new_games)} to the list of games! I already have {GetNames(already_exists)}, but I don't recognize {GetNames(failed_to_find)}.\n*Please select any of the games you're interested in playing below*", 
                            view = GameListView(ctx, ListType.Select, new_games | already_exists), files = await GetImages(new_games))

    @commands.command()
    async def remove_games(self, ctx):
        """Lists the collected games to select for removal."""
        # Lists the games to remove if there's more than zero. Otherwise reply with a passive agressive comment
        if len(games) > 0:
            message_sets = GetGameSets(games)

            set_count = 0
            while set_count < len(message_sets):
                if set_count == 0:
                    await ctx.reply(f"Here you go, {ctx.message.author.mention}. Please select the game(s) you'd like to remove...", view = GameListView(ctx, ListType.Remove, message_sets[set_count])) 
                else:
                    await ctx.reply(view = GameListView(ctx, ListType.Remove, message_sets[set_count]))
                set_count += 1
        else:
            await ctx.reply("This is where I would list my games... IF I HAD ANY!")