
import unicodedata
import requests
import discord
import difflib
import string
import math
import json
import os

from datetime import datetime, timedelta
from redbot.core import commands, bot
from difflib import SequenceMatcher
from discord.ext import tasks
from io import BytesIO
from enum import Enum
from PIL import Image

# Initializes intents
intents = discord.Intents(messages=True, guilds=True, members = True, presences = True)

# Initializes client with intents
client = discord.Client(intents = intents)

# List types
class ListType(Enum):
    Select_Game  = 1
    Remove_Game  = 2
    Remove_Alias = 3

# Sort types
class SortType(Enum):
    Alphabetical  = "Alphabetical"
    Popularity    = "Popularity"
    RecentlyAdded = "Recently Added"

# Flag types
class FlagType(Enum):
    Games    = 1
    Members  = 2
    Aliases  = 3
    Config   = 3

# Log Types
class LogType(Enum):
    Log     = "LOG"
    Debug   = "DEBUG"
    Warning = "WARNING"
    Error   = "ERROR"
    Fatal   = "FATAL"

# Navigation types
class NavigationType(Enum):
    First    = "First"
    Previous = "Previous"
    Sort     = "Sort Type"
    Next     = "Next"
    Last     = "Last"

# Cog Directory in Appdata
docker_cog_path  = "/data/cogs/AutoRolerPro"
games_file       = f"{docker_cog_path}/games.json"
members_file     = f"{docker_cog_path}/members.json"
aliases_file     = f"{docker_cog_path}/aliases.json"
config_file      = f"{docker_cog_path}/config.json"
log_file         = f"{docker_cog_path}/log.txt"

# Dictionary of updated file flags
update_flags = {
    FlagType.Games:   {'status': False, 'comment': ""}, 
    FlagType.Members: {'status': False, 'comment': ""}, 
    FlagType.Aliases: {'status': False, 'comment': ""}, 
    FlagType.Config:  {'status': False, 'comment': ""}
}

# Create the docker_cog_path if it doesn't already exist
os.makedirs(docker_cog_path, exist_ok = True)

default_config = {
    # Instantiates IGDB wrapper: https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/
    # curl -X POST "https://id.twitch.tv/oauth2/token?client_id=CLIENT_ID&client_secret=CLIENT_SECRET&grant_type=client_credentials"
    'IGDBCredentials': {
        'Client-ID': 'CHANGE-ME',
        'Authorization': 'CHANGE-ME'
    },
    'Links': {
        'GeneralChannel': "https://discord.com/channels/633799810700410880/633799810700410882"
    },
    'ChannelIDs' : {
        'General': 633799810700410882,
        'Bot': 634197647787556864,
        'Admin': 1013251079418421248,
        'Test': 665572348350693406
    },
    'WhitelistEnabled': True,
    'WhitelistMembers': ["sad.panda.", "agvv20", "ashlore.", "malicant999", "goldifish", "bad_ash85", "jucyblue", "explainablechaos", "deadinside6207", "camille26"],
    'AdminRole': 644687492569759791,
    'ActivityBlacklist': ["Spotify"],
    'DebugMode': True,
    'AliasMaxAttempts': 5,
    'BackupFrequency': 1,
    'AllowEroticTitles': False
}

# Initializes config
if os.path.isfile(config_file):
    with open(config_file, "r") as fp:
        config = json.load(fp)

    # Add missing default config entries
    for entry, value in default_config.items():
        if entry not in config:
            config[entry] = value
            update_flags[FlagType.Config] = {'status': True, 'comment': ""}

    # Saves the updated config file if necessary
    if update_flags[FlagType.Config]['status']:
        with open(config_file, "w") as fp:
            json.dump(config, fp, indent = 2, default = str, ensure_ascii = False)
else:
    config = default_config
    with open(config_file, "w") as fp:
        json.dump(config, fp, indent = 2, default = str, ensure_ascii = False)

# Initializes the games list
if os.path.isfile(games_file):
    with open(games_file, "r") as fp:
        games = json.load(fp)
else:
    games = {}
    with open(games_file, "w") as fp:
        json.dump(games, fp, indent = 2, default = str, ensure_ascii = False)

# Initializes the members list
if os.path.isfile(members_file):
    with open(members_file, "r") as fp:
        members = json.load(fp)
else:
    members = {}
    with open(members_file, "w") as fp:
        json.dump(members, fp, indent = 2, default = str, ensure_ascii = False)

# Initializes the aliases list
if os.path.isfile(aliases_file):
    with open(aliases_file, "r") as fp:
        aliases = json.load(fp)
else:
    aliases = {}
    with open(aliases_file, "w") as fp:
        json.dump(aliases, fp, indent = 2, default = str, ensure_ascii = False)

# Returns a string formatted datetime of now
def GetTime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

# Normalizes and strips accents from string
def strip_accents(s):
   return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')

# Updates the specified flag to queue for the backup routine
def UpdateFlag(flag: FlagType, status: bool = False, comment: str = ""):
    if not status:
        update_flags[flag] = {'status': False, 'comment': ""}
    else:
        update_flags[flag] = {'status': status, 'comment': f"{update_flags[flag]['comment']}\n  --{comment}"}

# Writes or appends a message to the log_file
def Log(message: str, log_type: LogType = LogType.Log):
    # Skips debug logs if debug mode is False
    if log_type == LogType.Debug and not config['DebugMode']:
        return
    
    # Initializes the log file or appends to an existing one
    if os.path.isfile(log_file):
        with open(log_file, "a") as fp:
            fp.write("\n")
            fp.writelines(f"{GetTime()}: ({log_type.value}) {message}")
    else:
        with open(log_file, "w") as fp:
            fp.writelines(f"{GetTime()}: ({log_type.value}) {message}")

# Returns a string list of game names
def GetNames(game_list: list):
    names = []
    # Loops through the game_list and appends to a list of names
    for game in game_list.values():
        names.append(game['name'])
    
    # Joins the names together in a string, separating each with a comma
    return f"`{'`, `'.join(names)}`"

# Returns a string list of role mentions
def GetRoles(game_list: list):
    roles = []
    # Loops through the game_list and appends to a list of role mentions
    for game in game_list.values():
        roles.append(f"<@&{game['role']}>")
    
    # Joins the role mentions together in a string, separating each with a comma
    return f"{', '.join(roles)}"

# Returns the cover art URL for the provided game_id
def GetCoverUrl(game_id):
    # Request the cover image urls
    db_json = requests.post('https://api.igdb.com/v4/covers', **{'headers' : config['IGDBCredentials'], 'data' : f'fields url; limit 1; where animated = false; where game = {game_id};'})
    results = db_json.json()

    if len(results) > 0:
        # Formats the cover URL
        url = f"https:{results[0]['url']}"
        url = url.replace("t_thumb", "t_cover_big")

        return url
    else:
        return None
    
# Returns a list of image files
async def GetImages(game_list: dict):
    images = []
    for game in game_list.values():
        # Request the http content of the game's cover url
        if 'cover_url' not in game:
            url = GetCoverUrl(game['id'])
            games[game['name']]['cover_url'] = url
            game['cover_url'] = url

            UpdateFlag(FlagType.Games, True, f"Added missing cover url to {game['name']}.")

        response = requests.get(game['cover_url'])
        img = Image.open(BytesIO(response.content))

        # Construct safe filename from game name
        filename = "".join(c for c in game['name'] if c.isalpha() or c.isdigit() or c == ' ').rstrip()

        # Convert PIL image to a useable binary image
        with BytesIO() as image_binary:
            img.save(image_binary, 'PNG')
            image_binary.seek(0)
            images.append(discord.File(fp=image_binary, filename=f"{filename}_cover.png"))

    return images

# Return a list of game sets containing a max of 25 games per set
def GetListSets(game_list: dict, set_amount: int, list_filter: str = None, sort: SortType = SortType.Alphabetical):
    if sort == SortType.Alphabetical:
        # Get a list of keys and sort them
        listKeys = list(game_list.keys())
        listKeys.sort()

        # Rebuild game_list using the sorted list of keys
        game_list = {i: game_list[i] for i in listKeys}

    elif sort == SortType.Popularity:
        # Get a list of keys sorted by playtime
        listKeys = list(GetPlaytime(game_list, 30).keys())

        # Rebuild game_list using the sorted list of keys
        game_list = {i: game_list[i] for i in listKeys}

    elif sort == SortType.RecentlyAdded:
        listKeys = list(games.keys())
        listKeys.reverse()

        new_list = {}
        # Loop through games and rebuild game_list 
        for game_name in listKeys:
            if game_name in game_list:
                new_list[game_name] = games[game_name]

        # Rebuild game_list using the sorted list of keys
        game_list = new_list


    list_sets = []
    item_count = 0
    for name, details in game_list.items():

        # Check eligability if there's a list_filter
        if list_filter:
            list_filter = list_filter.strip().lower()
            test_name = name.lower()
            similarity = SequenceMatcher(None, test_name, list_filter).ratio()
            Log(f"Similarity Score for {list_filter} and {test_name} is ({similarity}).", LogType.Debug)

            # If the list_filter is not in the name and similarity score is below 0.45, skip this game
            if list_filter not in test_name and similarity < 0.45:
                Log(f"Skipping {test_name}!", LogType.Debug)
                continue

        # Get the next index from set_amount
        idx = math.floor(item_count/set_amount)
        if idx < len(list_sets):
            list_sets[idx][name] = details
        else:
            list_sets.append({})
            list_sets[idx][name] = details

        # Iterate the number of items counted
        item_count += 1

    return list_sets

# Returns the dominant color of an image
def GetDominantColor(image_url: str, palette_size: int = 16):
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
def AddMember(member: discord.Member):
    # Collects the desired information about the member
    member_details = {}
    for detail in ['name', 'display_name', 'created_at', 'joined_at']:
        if hasattr(member, detail):
            member_details[detail] = getattr(member, detail)

    # Add server specific details to member record
    member_details['games'] = {}
    member_details['opt_out'] = False
    
    # Adds the member details to the members list
    members[member_details['name']] = member_details

    # Toggles the updated flag for members
    UpdateFlag(FlagType.Members, True, f"Added a new member, {member.name}")

# Update first dict with second recursively
def MergeDictionaries(d1: dict, d2: dict):
    if isinstance(d1, dict):
        for k, v in d1.items():
            if k in d2:
                d2[k] = MergeDictionaries(v, d2[k])
        d1.update(d2)
        return d1
    else:
        return d2

# Updates a member in the members list and saves file
def UpdateMember(member: discord.Member, new_details: dict):
    # Checks if member was previously added, if not, add them.
    if member.name not in members:
        AddMember(member)

    # Updates specific member with new details using the recursive MergeDictionaries function
    MergeDictionaries(members[member.name], new_details)
    
    # Toggles the updated flag for members
    UpdateFlag(FlagType.Members, True, f"Updated member information, {member.name}")

# Removes game from games list and saves to file
async def RemoveGame(role: discord.Role, game_name: str):
    if game_name in games:
        # Delete the role if found, if role doesn't exist, do nothing
        if role:
            await role.delete()
        else:
            Log(f"Failed to remove game. Could not find this role: `{game_name}`!", LogType.Warning)

        del games[game_name]

        # Toggles the updated flag for games
        UpdateFlag(FlagType.Games, True, f"Removed a game, {game_name}")
        
        return True
    else:
        Log(f"Failed to remove game. Could not find {game_name} in list.", LogType.Error)
        return False

# Adds a list of games to the games list after verifying they are real games
async def AddGames(guild: discord.Guild, game_list: list):
    new_games      = {}
    already_exists = {}
    failed_to_find = {}

    def AlreadyExists(game_name):
        if "role" not in games[game_name]:
            # Looks for an existing role for the game
            role = discord.utils.get(guild.roles, name = game_name)
            if role:
                # Stores the role for future use
                games[game_name]['role'] = role.id

                # Toggles the updated flag for games
                UpdateFlag(FlagType.Games, True, f"Added missing role entry for the {game_name} game!")

        if game_name in aliases:
            already_exists[aliases[game_name]] = games[aliases[game_name]]
        else:
            already_exists[game_name] = games[game_name]

    # Loops through the provided list of game names
    for game_name in game_list:
        # Checks if game already exists to avoid unnecessary API calls
        if game_name in games or game_name in aliases:
            AlreadyExists(game_name)
        else:
            # Debug log the difference before and after the strip_accents function call
            Log(game_name, LogType.Debug)
            game_name = string.capwords(strip_accents(game_name))
            Log(game_name, LogType.Debug)

            # Check if erotic titles are allowed in the config
            if config['AllowEroticTitles']:
                if game_name.isnumeric():
                    # Request the game title with the provided game id
                    Log(f"Looking for game id {game_name}", LogType.Debug)
                    db_json = requests.post('https://api.igdb.com/v4/games', **{'headers' : config['IGDBCredentials'], 'data' : f'fields name,summary,first_release_date; limit 1; where id = {int(game_name)};'})
                else:
                    # Request all game titles that match the game name
                    db_json = requests.post('https://api.igdb.com/v4/games', **{'headers' : config['IGDBCredentials'], 'data' : f'search "{game_name}"; fields name,summary,first_release_date; limit 500; where summary != null;'})
            else:
                if game_name.isnumeric():
                    # Request the game title with the provided game id
                    Log(f"Looking for game id {game_name}", LogType.Debug)
                    db_json = requests.post('https://api.igdb.com/v4/games', **{'headers' : config['IGDBCredentials'], 'data' : f'fields name,summary,first_release_date; limit 1; where id = {int(game_name)} & themes != (42);'})
                else:
                    # Request all game titles that match the game name while filtering out titles with the 42 ('erotic') theme.
                    db_json = requests.post('https://api.igdb.com/v4/games', **{'headers' : config['IGDBCredentials'], 'data' : f'search "{game_name}"; fields name,summary,first_release_date; limit 500; where summary != null & themes != (42);'})

            # Converts the json database response to a usable dictionary results variable
            results = db_json.json()

            # Exits if 'cause' exists in results, this is indicative of an error
            if 'cause' in results:
                Log(str(results), LogType.Error)
                return
            else:
                Log(str(results), LogType.Debug)

            # Collect the game names
            game_names = [details['name'] for details in results]

            # Check if game is numeric, skip looking for matches
            if game_name.isnumeric():
                matches = None
            else:
                # Get the top match for the provided name
                matches = difflib.get_close_matches(game_name, game_names, 1)

            # Compares the list of games to the matches, from there sort by release year
            latest_game = None
            for game_details in results:
                if latest_game and (game_name.isnumeric() or game_details['name'] in matches):
                    latest_year = datetime.utcfromtimestamp(latest_game['first_release_date']).strftime('%Y')
                    release_year = datetime.utcfromtimestamp(game_details['first_release_date']).strftime('%Y')
                    if release_year > latest_year:
                        latest_game = game_details
                elif game_name.isnumeric() or game_details['name'] in matches:
                    latest_game = game_details

            # Checks if game already exists again with the nearly found game name
            if latest_game and (latest_game['name'] in games or latest_game['name'] in aliases):
                AlreadyExists(latest_game['name'])
            elif latest_game:
                # Get cover url from game id
                url = GetCoverUrl(latest_game["id"])

                # Stores the formatted URL in the latest game dictionary
                latest_game['cover_url'] = url
                
                # Create the Role and give it the dominant color of the cover art
                color = GetDominantColor(url)
                
                # Looks for an existing role for the game
                role = discord.utils.get(guild.roles, name = latest_game['name'])
                if role:
                    await role.edit(colour = discord.Colour(int(color, 16)))
                else:
                    role = await guild.create_role(name = latest_game['name'], colour = discord.Colour(int(color, 16)), mentionable = True)

                # Stores the role for future use
                latest_game['role'] = role.id

                # Adds the latest_game to the new_games list to return
                new_games[latest_game['name']] = latest_game

                # Add game to game list and saves file
                games[latest_game['name']] = latest_game

                # Toggles the updated flag for games
                UpdateFlag(FlagType.Games, True, f"Added new game, {latest_game['name']}, and it's associated role to the server!")
            else:
                failed_to_find[game_name] = {'name' : game_name, 'summary' : 'unknown', 'first_release_date' : 'unknown'}
        
    return new_games, already_exists, failed_to_find

# Adds an alias and game to the aliases list, adds the game if it doesn't already exist
async def AddAlias(bot: discord.Client, guild: discord.Guild, alias: str, member: discord.Member = None):
    # Get the admin and test text channels
    admin_channel = guild.get_channel(config['ChannelIDs']['Admin'])
    test_channel = guild.get_channel(config['ChannelIDs']['Test'])

    # Send the original message
    if member:
        original_message = await admin_channel.send(f"{member.mention} started playing `{alias}`, but I can't find it in the database!\n*Please reply with the full name associated with this game!*")
    else:
        original_message = await admin_channel.send(f"So you want to set up `{alias}` as an alias, huh? Reply with the full name of the game associated with this alias!")

    # Sets up a loop to allow for multiple attempts at setting a name
    game = None
    attempt_count = 0
    while not game and attempt_count < config['AliasMaxAttempts']:
        # Returns true of the message is a reply to the original message
        def check(message):
            return message.reference and message.reference.message_id == original_message.id

        # Wait for a reply in accordance with the check function
        msg = await bot.wait_for('message', check = check)
        
        # Add the msg.content as a game to the server
        new_games, already_exists, failed_to_find = await AddGames(guild, [msg.content])

        # Decrement remaining_attempts by 1
        remaining_attempts = config['AliasMaxAttempts'] - attempt_count - 1

        # If a new or existing game is found, assign it to game to exit the loop
        if len(new_games) > 0:
            game = list(new_games.values())[0]
        elif len(already_exists) > 0:
            game = list(already_exists.values())[0]
        elif len(failed_to_find) > 0 and remaining_attempts > 0:
            original_message = await msg.reply(f"I was unable to assign `{alias}` to a game - I couldn't find `{msg.content}` in the database!\n*Please try again by replying to this message! Attempts remaining: {remaining_attempts}*")
            attempt_count += 1
    
    # Update alias if a game was ultimately found
    if game:
        # Assign game to the new alias
        aliases[alias] = game['name']

        # Toggles the updated flag for aliases
        UpdateFlag(FlagType.Aliases, True, f"Assigned a new alias, {alias}, to the {game['name']} game!")

        # Once a game is found, it sets the alias and exits
        await msg.reply(f"Thanks, {msg.author.mention}! I've given <@&{game['role']}> an alias of `{alias}`.", files = await GetImages({game['name'] : game}))
    else:
        await msg.reply(f"Thanks for the attempt, {msg.author.mention}, but I wasn't able to find any games to assign the alias `{alias}` to!\n*Try again with `!set_alias {alias}`*")

# Removes a specific alias from the aliases list
def RemoveAlias(alias_name: str):
    if alias_name in aliases:
        del aliases[alias_name]

        # Toggles the updated flag for aliases
        UpdateFlag(FlagType.Aliases, True, f"Removed the {alias_name} alias.")

        return True 
    else:
        return False

# Handles tracking of gameplay when someone starts playing
def StartPlayingGame(member: discord.Member, game_name: str):
    # Checks of game_name is an alias; if not and game_name is also not in games, return and log failure
    if game_name in aliases:
        game_name = aliases[game_name]
    else:
        try:
            game_name = [game for game in games if game.lower() == game_name.lower()][0]
        except:
            Log(f"Could not find {game_name} in the game list or aliases when {member.name} started playing!", LogType.Warning)
            return
            
    # Grabs the current YYYY-MM-DD from the current datetime
    date = datetime.now().strftime('%Y-%m-%d')

    # Constructs history dictionary for game if missing
    if 'history' not in games[game_name]:
        games[game_name]['history'] = {}
    
    # Adds the current date to the game's history if missing
    if date not in games[game_name]['history']:
        games[game_name]['history'][date] = {}

    # Adds the member to the current date if missing
    if member.name not in games[game_name]['history'][date]:
        games[game_name]['history'][date][member.name] = {}
    
    # Sets the member's last_played datetime for the current day and game
    games[game_name]['history'][date][member.name]['last_played'] = GetTime()

    # Toggles the updated flag for games
    UpdateFlag(FlagType.Games, True, f"{member.name} started playing {game_name}")

# Records number of hours played since member started playing game and tallies for the day
def StopPlayingGame(member: discord.Member, game_name: str):
    # Checks if game_name is an alias; if not and game_name is also not in games, return and log failure
    if game_name in aliases:
        game_name = aliases[game_name]
    else:
        try:
            game_name = [game for game in games if game.lower() == game_name.lower()][0]
        except:
            Log(f"Could not find {game_name} in the game list or aliases when {member.name} stopped playing!", LogType.Warning)
            return

    # Checks if game has history, log error if missing
    if 'history' not in games[game_name]:
        Log(f"Could not find history for {game_name} after {member.name} stopped playing!", LogType.Error)
        return
    
    def AddPlaytime(date, hours):
        # Adds playtime to the current date and member if missing
        if 'playtime' not in games[game_name]['history'][date][member.name]:
            games[game_name]['history'][date][member.name]['playtime'] = 0

        # Add hours to playtime for the day
        games[game_name]['history'][date][member.name]['playtime'] = round(games[game_name]['history'][date][member.name]['playtime'] + hours, 2)

        # Remove last_played when it's accounted for
        if 'last_played' in games[game_name]['history'][date][member.name]:
            del games[game_name]['history'][date][member.name]['last_played']

        # Toggles the updated flag for games
        UpdateFlag(FlagType.Games, True, f"{member.name} stopped playing {game_name}")
    
    # Grabs today and yesterday's YYYY-MM-DD from the current datetime
    today     = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days = 1)).strftime('%Y-%m-%d')

    if today in games[game_name]['history']:
        # Verifies that member has history for today, logs error if not
        if member.name not in games[game_name]['history'][today]:
            Log(f"Could not find member in history for {game_name} after {member.name} stopped playing!", LogType.Error)
            return
        
        # Get the difference in time between last_played and now
        last_played = games[game_name]['history'][today][member.name]['last_played']
        delta_time = datetime.now() - datetime.strptime(last_played, '%Y-%m-%d %H:%M:%S.%f')

        # Convert delta_time to hours and round to 2 decimal places
        hours = round(delta_time.total_seconds()/3600, 2)

        # Add playtime for today
        AddPlaytime(today, hours)
    else:
        # Check if there's a last_played in yesterday's history
        if yesterday in games[game_name]['history'] and member.name in games[game_name]['history'][yesterday] and 'last_played' in games[game_name]['history'][yesterday][member.name]:
            Log(f"{member.name} played {game_name} overnight, splitting time across two days!", LogType.Log)

            # Get yesterday's last_played time and midnight
            last_played  = games[game_name]['history'][yesterday][member.name]['last_played']
            midnight = (datetime.strptime(last_played, '%Y-%m-%d %H:%M:%S.%f') + timedelta(days=1)).replace(hour=0, minute=0, microsecond=0, second=0)
            
            # Convert delta_time to hours and round to 2 decimal places
            delta_time = midnight - datetime.strptime(last_played, '%Y-%m-%d %H:%M:%S.%f')
            hours = round(delta_time.total_seconds()/3600, 2)

            # Add playtime for yesterday
            AddPlaytime(yesterday, hours)

            # Convert delta_time to hours and round to 2 decimal places
            delta_time = datetime.now() - midnight
            hours = round(delta_time.total_seconds()/3600, 2)

            # Adds the current date to the game's history if missing
            if today not in games[game_name]['history']:
                games[game_name]['history'][today] = {}

            # Adds the member to the current date if missing
            if member.name not in games[game_name]['history'][today]:
                games[game_name]['history'][today][member.name] = {}

            # Add playtime for today
            AddPlaytime(today, hours)
        else:
            Log(f"Could not determine {member.name}'s play session for {game_name}! Maybe it spanned more than 2 days?", LogType.Warning)

            # Loop through all of the dates in the game's history
            for date in games[game_name]['history']: 
                if member.name in games[game_name]['history'][date] and 'last_played' in games[game_name]['history'][date][member.name]:
                    # Log the last_played and then delete the entry
                    Log(f"Found {member.name}'s last_played datetime for {game_name}: {games[game_name]['history'][date][member.name]['last_played']}", LogType.Log)
                    del games[game_name]['history'][date][member.name]['last_played']

                    # Toggles the updated flag for games
                    UpdateFlag(FlagType.Games, True, f"Removed {member.name}'s old play history from {game_name}.")

# Gets the total playtime over the last number of given days. Include optional member to filter
def GetPlaytime(game_list: dict, days: int, count: int = None, member: discord.Member = None):
    top_games = {}
    for game_name, game_value in game_list.items():
        # Initializes the gameplay dictionary with zeros for each game
        top_games[game_name] = 0

        # Skips game if there's not history
        if 'history' not in game_value:
            continue
        
        for day, day_value in game_value['history'].items():
            # Checks if day is within the number of days specified
            if datetime.strptime(day, '%Y-%m-%d') > datetime.now() - timedelta(days = days):
                for name, details in day_value.items():
                    # If member is provided, filter by their name
                    if (member == None or name == member.name) and 'playtime' in details:
                        top_games[game_name] += details['playtime']
        
        # Rounds the game playtime to 2 decimal places
        top_games[game_name] = round(top_games[game_name], 2)

    if count:
        # Sort the list by highest hours played and shrink to count
        sorted_list = sorted(top_games.items(), key = lambda x:x[1], reverse=True)[:count]
    else: 
        # Sort the entire list by highest hours played
        sorted_list = sorted(top_games.items(), key = lambda x:x[1], reverse=True)

    return dict(sorted_list)

# Create a class called DirectMessageView that subclasses discord.ui.View
class DirectMessageView(discord.ui.View):
    def __init__(self, original_message: str, role: discord.Role, member: discord.Member, game):
        super().__init__(timeout = 60 * 60 * 12) # Times out after 12 hours
        
        self.original_message = original_message
        self.role = role
        self.member = member
        self.game = game

        self.add_item(self.YesButton(self.original_message, self.role, self.member, self.game))
        self.add_item(self.NoButton(self.original_message, self.role, self.member, self.game))
        self.add_item(self.OptOutButton(self.original_message, self.role, self.member, self.game))

    # Create a class called YesButton that subclasses discord.ui.Button
    class YesButton(discord.ui.Button):
        def __init__(self, original_message, role, member, game):
            super().__init__(label = "YES", style = discord.ButtonStyle.success, emoji = "😀")
            self.original_message = original_message
            self.role = role
            self.member = member
            self.game = game

        async def callback(self, interaction):
            try:
                # Assign role to member
                await self.member.add_roles(self.role)
                
                # Records answer for this game and the current datetime for last played
                update = {'games' : {self.game['name'] : {'tracked' : True}}}
                UpdateMember(self.member, update)

                # Responds to the request
                await interaction.message.edit(content = f"{self.original_message}\n*You've selected `YES`*", view = None)
                await interaction.response.send_message(f"Awesome! I've added you to the `{self.game['name']}` role! Go ahead and mention the role in the [server]({config['Links']['GeneralChannel']}) to meet some new friends!")
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, something went wrong! I was unable to assign the `{self.game['name']}` role to you. Please check the logs for further details.")
                Log(error, LogType.Error)
                raise Exception(error)
                
    # Create a class called NoButton that subclasses discord.ui.Button             
    class NoButton(discord.ui.Button):
        def __init__(self, original_message, role, member, game):
            super().__init__(label = "NO", style = discord.ButtonStyle.secondary, emoji = "😕")
            self.original_message = original_message
            self.role = role
            self.member = member
            self.game = game

        async def callback(self, interaction):
            try:
                # Remove role from member if exists
                if self.role in self.member.roles:
                    await self.member.remove_roles(self.role)

                # Records answer for this game and the current datetime for last played
                update = {'games' : {self.role.name : {'tracked' : False}}}
                UpdateMember(self.member, update)
                
                await interaction.message.edit(content = f"{self.original_message}\n*You've selected `NO`*", view = None)
                await interaction.response.send_message(f"Understood! I won't ask about `{self.game['name']}` again! Feel free to manually add yourself anytime using the `!list_games` command in the [server]({config['Links']['GeneralChannel']})!")
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, I was unable to complete the requested command! Please check the logs for further details.")
                Log(error, LogType.Error)
                raise Exception(error)
              
    # Create a class called OptOutButton that subclasses discord.ui.Button                   
    class OptOutButton(discord.ui.Button):
        def __init__(self, original_message, role, member, game):
            super().__init__(label = "OPT OUT", style = discord.ButtonStyle.danger, emoji = "😭")
            self.original_message = original_message
            self.role = role
            self.member = member
            self.game = game

        async def callback(self, interaction):
            try:
                # Updates the out_out flag for the member
                update = {'opt_out' : True}
                UpdateMember(self.member, update)

                await interaction.message.edit(content = f"{self.original_message}\n*You've selected `OPT OUT`*", view = None)
                await interaction.response.send_message(f"Sorry to bother! I've opted you out of the automatic role assignment! If in the future you'd like to opt back in, simply use the `!opt_in` command anywhere in the [server]({config['Links']['GeneralChannel']})!")
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, I was unable to complete the requested command! Please check the logs for further details.")
                Log(error, LogType.Error)
                raise Exception(error)

    async def on_timeout(self):
        # TODO: Make this edit dynamic based on what the user selected (or didn't)
        await self.message.edit(content = f"{self.original_message}\n*This request has timed out! If you didn't get to this already, you can still add youself to the roll manually by using the command `!list_games` in the [server]({config['Links']['GeneralChannel']})!*", view = None)

# Create a class called PageView that subclasses discord.ui.View
class PageView(discord.ui.View):
    def __init__(self, original_message: str, list_type: ListType, list_sets: list, list_filter: str, page: int, guild: discord.Guild, member: discord.Member = None, sort: SortType = SortType.Alphabetical):
        super().__init__(timeout = 60 * 60 * 12) # Times out after 12 hours 
        self.original_message = original_message
        self.member = member
    
        if len(list_sets) > 1:
            # Populate the navigation buttons
            for nav_type in NavigationType:
                self.add_item(self.NavigateButton(nav_type, original_message, list_type, list_sets, list_filter, page, guild, member, sort))

        # Populate the game buttons
        for name, details in list_sets[page - 1].items():
            self.add_item(self.ItemButton(original_message, list_type, name, details, list_sets, list_filter, page, guild, member, sort))
        
    class NavigateButton(discord.ui.Button):
        def __init__(self, nav_type: NavigationType, original_message: str, list_type: ListType, list_sets: list, list_filter: str, page: int, guild: discord.Guild, member: discord.Member, sort: SortType):
            self.nav_type = nav_type
            self.original_message = original_message
            self.list_type = list_type
            self.list_sets = list_sets
            self.list_filter = list_filter
            self.guild = guild
            self.member = member
            self.sort = sort
            self.page_count = len(self.list_sets)

            if self.nav_type == NavigationType.First:
                super().__init__(label = nav_type.value, style = discord.ButtonStyle.primary, emoji = "⏮️")
                self.goto = 1
            elif self.nav_type == NavigationType.Previous:
                super().__init__(label = nav_type.value, style = discord.ButtonStyle.primary, emoji = "◀️")
                self.goto = page - 1
            elif self.nav_type == NavigationType.Sort:
                super().__init__(label = nav_type.value, style = discord.ButtonStyle.primary, emoji = "📄") #📄⚙️
                self.goto = 1
            elif self.nav_type == NavigationType.Next:
                super().__init__(label = nav_type.value, style = discord.ButtonStyle.primary, emoji = "▶️")
                self.goto = page + 1
            elif self.nav_type == NavigationType.Last:
                super().__init__(label = nav_type.value, style = discord.ButtonStyle.primary, emoji = "⏭️")
                self.goto = self.page_count

            if page == 1 and (nav_type == NavigationType.First or nav_type == NavigationType.Previous):
                self.disabled = True
            elif page == 2 and nav_type == NavigationType.First:
                self.disabled = True
            elif page == (self.page_count - 1) and nav_type == NavigationType.Last:
                self.disabled = True
            elif page == self.page_count and (nav_type == NavigationType.Last or nav_type == NavigationType.Next):
                self.disabled = True

        async def callback(self, interaction):
            # Prevent other people from messing with your page buttons
            if self.member and self.member != interaction.user:
                if self.list_type is ListType.Select_Game:
                    await interaction.response.send_message(f"You're not {self.member.mention}! Who are you?\n*Please use `!list_pages` to interact!*", ephemeral = True, delete_after = 10)
                else:
                    await interaction.response.send_message(f"You're not {self.member.mention}! Who are you?", ephemeral = True, delete_after = 10)
                return
            
            # If the sort button is pressed, update message with the next sort type
            if self.nav_type == NavigationType.Sort:
                if self.sort == SortType.Alphabetical:
                    self.sort = SortType.Popularity
                elif self.sort == SortType.Popularity:
                    self.sort = SortType.RecentlyAdded
                elif self.sort == SortType.RecentlyAdded:
                    self.sort = SortType.Alphabetical

                self.list_sets = GetListSets(games, 20, self.list_filter, self.sort)
                self.page_count = len(self.list_sets)

            # Repopulate message based on the last interaction
            view = PageView(self.original_message, self.list_type, self.list_sets, self.list_filter, self.goto, self.guild, self.member, self.sort)
            if self.list_type is ListType.Select_Game:
                view.message = await interaction.response.edit_message(content = f"{self.original_message}\n*`{self.sort.value}: (Page {self.goto} of {self.page_count})` Please select the games that you're interested in playing:*", view = view)
            if self.list_type is ListType.Remove_Game:
                view.message = await interaction.response.edit_message(content = f"{self.original_message}\n*`{self.sort.value}: (Page {self.goto} of {self.page_count})` Please select the game(s) you'd like to remove...*", view = view)
            if self.list_type is ListType.Remove_Alias:
                view.message = await interaction.response.edit_message(content = f"{self.original_message}\n*`{self.sort.value}: (Page {self.goto} of {self.page_count})` Please select the aliases you'd like to remove...*", view = view)
                
            
    class ItemButton(discord.ui.Button):
        def __init__(self, original_message: str, list_type: ListType, name: str, details: dict, list_sets: list, list_filter: str, page: int, guild: discord.Guild, member: discord.Member, sort: SortType):
            # Instantiate button variables
            self.original_message = original_message
            self.list_type = list_type
            self.name = name
            self.details = details
            self.list_sets = list_sets
            self.list_filter = list_filter
            self.page = page
            self.guild = guild
            self.member = member
            self.sort = sort

            # Grabs role from guild
            if list_type is ListType.Remove_Alias:
                self.role = None
            else:
                self.role = self.guild.get_role(self.details['role'])

            # Check if member has the role and set button color accordingly
            if self.member:
                if self.role in self.member.roles:
                    button_style = discord.ButtonStyle.success
                else:
                    button_style = discord.ButtonStyle.secondary
            else:
                button_style = discord.ButtonStyle.primary

            super().__init__(label = self.name, style = button_style)

        async def callback(self, interaction):
            if self.member and self.member != interaction.user:
                if self.list_type is ListType.Select_Game:
                    await interaction.response.send_message(f"You're not {self.member.mention}! Who are you?\n*Please use `!list_games` to interact!*", ephemeral = True, delete_after = 10)
                else:
                    await interaction.response.send_message(f"You're not {self.member.mention}! Who are you?", ephemeral = True, delete_after = 10)
                return

            # Should not be missing role by this stage, log error if missing
            if self.list_type != ListType.Remove_Alias and self.role == None:
                error_message = f"Something went wrong, I can't find the associated role for `{self.name}`.\nPlease try adding the game again using `!add_games {self.name}`"
                
                # Log error and message user about failure
                Log(error_message, LogType.Error)
                await interaction.response.send_message(error_message, ephemeral = True)

                # Do not continue if role is missing
                return
            
            if self.list_type is ListType.Select_Game:
                # Looks for the role with the same name as the game
                if self.role:
                    if self.role in interaction.user.roles:
                        # Assign role to member
                        member = interaction.user
                        await member.remove_roles(self.role)

                        # Updates member details
                        update = {'games' : {self.name : {'tracked' : False}}}
                        UpdateMember(member, update)

                        view = PageView(self.original_message, ListType.Select_Game, self.list_sets, self.list_filter, self.page, self.guild, self.member, self.sort)
                        view.message = await interaction.message.edit(view = view)

                        await interaction.response.send_message(f"I have removed you from the `{self.name}` role! I'll also not message you in the future regarding this particular game!", ephemeral = True, delete_after = 10)
                    else:
                        # Assign role to member
                        member = interaction.user
                        await member.add_roles(self.role)

                        # Updates member details
                        update = {'games' : {self.name : {'tracked' : True}}}
                        UpdateMember(member, update)

                        view = PageView(self.original_message, ListType.Select_Game, self.list_sets, self.list_filter, self.page, self.guild, self.member, self.sort)
                        view.message = await interaction.message.edit(view = view)

                        # Informs the user that the role has been assigned to them
                        await interaction.response.send_message(f"Added you to the `{self.name}` role!", ephemeral = True, delete_after = 10)
                else:
                    await interaction.response.send_message(f"Something went wrong, I can't find the associated role for `{self.name}`.\nPlease try adding the game again using !add_games {self.name}", ephemeral = True)

            elif self.list_type is ListType.Remove_Game:
                # Tries to remove the game, returns false if it fails
                if await RemoveGame(self.role, self.name):
                    self.list_sets = GetListSets(games, 20, self.list_filter, self.sort)
                    self.page_count = len(self.list_sets)

                    # Check if deleted last item on the page, if so, set page to last page
                    if self.page > self.page_count:
                        self.page = self.page_count
                    
                    view = PageView(self.original_message, self.list_type, self.list_sets, self.list_filter, self.page, self.guild, self.member, self.sort)
                    view.message = await interaction.message.edit(content = f"{self.original_message}\n*`{self.sort.value}: (Page {self.page} of {self.page_count})` Please select the game(s) you'd like to remove...*", view = view)

                    await interaction.response.send_message(f"I have removed {self.name} from the list!", ephemeral = True, delete_after = 10)
                else:
                    await interaction.response.send_message(f"I couldn't removed {self.name} from the list!\n*Check out the log for more details!*", ephemeral = True, delete_after = 10)

            elif self.list_type is ListType.Remove_Alias:
                # Tries to remove the alias, returns false if it fails
                if RemoveAlias(self.name):
                    self.list_sets = GetListSets(aliases, 20, self.list_filter, self.sort)
                    self.page_count = len(self.list_sets)

                    # Check if deleted last item on the page, if so, set page to last page
                    if self.page > self.page_count:
                        self.page = self.page_count

                    view = PageView(self.original_message, self.list_type, self.list_sets, self.list_filter, self.page, self.guild, self.member, self.sort)
                    view.message = await interaction.message.edit(content = f"{self.original_message}\n*`{self.sort.value}: (Page {self.page} of {self.page_count})` Please select the aliases you'd like to remove...*", view = view)

                    await interaction.response.send_message(f"`{self.name}` has been removed from the list!")
                else:
                    await interaction.response.send_message(f"Unable to remove `{self.name}` - I could not find it in the list of aliases!")

    async def on_timeout(self):
        if not self.original_message:
            await self.message.delete()
        else:
            if self.member and self.message:
                await self.message.edit(content = f"{self.original_message}\n*This request has timed out! If you hadn't finished, please try again!*", view = None)
            else:
                await self.message.edit(content = f"{self.original_message}", view = None)

# Create a class called PlaytimeView that subclasses discord.ui.View
class PlaytimeView(discord.ui.View):
    def __init__(self, original_message: str, member: discord.Member = None):
        super().__init__(timeout = 60 * 60 * 12) # Times out after 12 hours 

        self.original_message = original_message
        self.member = member

        self.add_item(self.ServerButton(self.original_message, self.member))
        self.add_item(self.SelfButton(self.original_message))

    # Create a class called YesButton that subclasses discord.ui.Button
    class ServerButton(discord.ui.Button):
        def __init__(self, original_message: str, member: discord.Member):
            super().__init__(label = "Server", style = discord.ButtonStyle.secondary, emoji = "💻")
            self.original_message = original_message
            self.member = member

        async def callback(self, interaction):
            try:
                # Initialize the playtime message and game refernces for the games played
                playtime_message = ""
                game_refs = {}
                for game_name, time in GetPlaytime(games, 30, 5).items():
                    # Store a reference of the game data in game_refs
                    game_refs[game_name] = games[game_name]

                    # Calculate hours and minutes from time and add to playtime_message
                    hours, minutes = divmod(time*60, 60)
                    playtime_message += f"- **{game_name}** *({int(hours)}h:{int(minutes)}m)*\n"

                await interaction.response.send_message(f"Check out this server's top 5 games this month!\n{playtime_message}", files = await GetImages(game_refs))
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, something went wrong! I was unable to grab the server's top 5 games for this month. Please check the logs for further details.", ephemeral = True)
                Log(error, LogType.Error)
                raise Exception(error)

    class SelfButton(discord.ui.Button):
        def __init__(self, original_message: str):
            super().__init__(label = "Self", style = discord.ButtonStyle.secondary, emoji = "😁")
            self.original_message = original_message

        async def callback(self, interaction):
            try:            
                # Get the list of the top # of games
                playtime_list = GetPlaytime(games, 30, 5, interaction.user)
                if playtime_list:
                    # Initialize the playtime message and game refernces for the games played
                    playtime_message = ""
                    game_refs = {}
                    for game_name, time in playtime_list.items():
                        # Only list games with more than 0 time
                        if time > 0:
                            # Store a reference of the game data in game_refs
                            game_refs[game_name] = games[game_name]
                            
                            # Calculate hours and minutes from time and add to playtime_message
                            hours, minutes = divmod(time*60, 60)
                            playtime_message += f"- **{game_name}** *({int(hours)}h:{math.ceil(minutes)}m)*\n"

                    await interaction.response.send_message(f"Here you go, {interaction.user.mention}! These are your top games this month!\n{playtime_message}", ephemeral = True, files = await GetImages(game_refs))
                else:
                    await interaction.response.send_message(f"Hey, {interaction.user.mention}! Looks like I haven't tracked you playing any games for the last 30 days!", ephemeral = True)

            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, something went wrong! I was unabe to grab your top 5 games for this month. Please check the logs for further details.", ephemeral = True)
                Log(error, LogType.Error)
                raise Exception(error)
            
    async def on_timeout(self):
        await self.message.edit(content = f"{self.original_message}\n*This request has timed out! If you hadn't finished, please try again!*", view = None)

class AutoRolerPro(commands.Cog):
    """My custom cog"""
    def __init__(self, bot: bot.Red):
        self.bot = bot
        Log("AutorolerPro loaded!", LogType.Log)

        # Start the backup routine
        self.BackupRoutine.start()
    
    async def cog_unload(self):
        self.BackupRoutine.cancel()

    @tasks.loop(minutes = config['BackupFrequency'])
    async def BackupRoutine(self):
        # Initializes the log message
        log_message = f"Initiating routine data backup sequence ------------------------------"

        # Returns true if games flag is updated
        game_flag = update_flags[FlagType.Games]
        if game_flag['status']:
            with open(games_file, "w") as fp:
                json.dump(games, fp, indent = 2, default = str, ensure_ascii = False) 

            # Adds games file update to log message
            log_message += f"\n  Successfully saved to {games_file} {game_flag['comment']}"

            # Resets flag
            UpdateFlag(FlagType.Games)
        else:
            # Adds aliases file update to log message
            Log("Games file not updated, no changes.", LogType.Debug)

        # Returns true if members flag is updated
        game_flag = update_flags[FlagType.Members]
        if game_flag['status']:
            with open(members_file, "w") as fp:
                json.dump(members, fp, indent = 2, default = str, ensure_ascii = False)
            
            # Adds members file update to log message
            log_message += f"\n  Successfully saved to {members_file}! {game_flag['comment']}"

            # Resets flag
            UpdateFlag(FlagType.Members)
        else:
            # Adds aliases file update to log message
            Log("Members file not updated, no changes.", LogType.Debug)

        # Returns true if aliases flag is updated
        game_flag = update_flags[FlagType.Aliases]
        if game_flag['status']:
            with open(aliases_file, "w") as fp:
                json.dump(aliases, fp, indent = 2, default = str, ensure_ascii = False)
            
            # Adds aliases file update to log message
            log_message += f"\n  Successfully saved to {aliases_file}! {game_flag['comment']}"

            # Resets flag
            UpdateFlag(FlagType.Aliases)
        else:
            # Adds aliases file update to log message
            Log("Aliases file not updated, no changes.", LogType.Debug)

        # Returns true if aliases flag is updated
        game_flag = update_flags[FlagType.Config]
        if game_flag['status']:
            with open(config_file, "w") as fp:
                json.dump(config, fp, indent = 2, default = str, ensure_ascii = False)
            
            # Adds aliases file update to log message
            log_message += f"\n  Successfully saved to {config_file}! {game_flag['comment']}"

            # Resets flag
            UpdateFlag(FlagType.Config)
        else:
            # Adds aliases file update to log message
            Log("Config file not updated, no changes.", LogType.Debug)

        # Logs the events of the backup routine
        Log(log_message, LogType.Log)

    # Detect when a member's presence changes
    @commands.Cog.listener(name='on_presence_update')
    async def on_presence_update(self, previous: discord.Member, current: discord.Member):
        # Get important information about the context of the event
        general_channel = current.guild.get_channel(config['ChannelIDs']['General'])
        bot_channel = current.guild.get_channel(config['ChannelIDs']['Bot'])
        admin_channel = current.guild.get_channel(config['ChannelIDs']['Admin'])
        test_channel = current.guild.get_channel(config['ChannelIDs']['Test'])

        # Exits if not SadPanda for DEBUGGING
        if current.name != "sad.panda.":
            return

        # Exits if the WhitelistEnabled is true and member isn't whitelisted
        if config['WhitelistEnabled'] and current.name not in config['WhitelistMembers']:
            return

        # Adds member to members dictionary for potential tracking (will ask if they want to opt-out)
        if current.name not in members:
            AddMember(current)

        # Assigns member with current.name
        member = members[current.name]
        
        # Collect the activity names
        previous_names = [activity.name for activity in previous.activities]
        current_names = [activity.name for activity in current.activities]

        # Loops through previous activities and check if they don't exist in current names
        for activity in previous.activities:
            if activity.name not in current_names and activity.type == discord.ActivityType.playing:
                # Exit if game is blacklisted
                if activity.name in config['ActivityBlacklist']:
                    return
                
                await admin_channel.send(f"`{member['display_name']}` stopped playing `{activity.name}`")
                StopPlayingGame(current, activity.name)

        # Loops through previous activities and check if they don't exist in previous names
        for activity in current.activities:
            if activity.name not in previous_names and activity.type == discord.ActivityType.playing:
                # Exit if game is blacklisted
                if activity.name in config['ActivityBlacklist']:
                    return
                
                # Checks of the activity is an alias first to avoid a potentially unnecessary API call
                if activity.name in aliases:
                    game_name = aliases[current.activity.name]
                    if game_name in games:
                        game = games[game_name]
                    else:
                        await admin_channel.send(f"`{member['display_name']}` started playing `{activity.name}`, and I found an alias with that name, but the game associated with it isn't in the list! Not sure how that happened!")
                        return
                else:
                    # If there isn't a game recorded for the current activity already, add it
                    new_games, already_exists, failed_to_find = await AddGames(current.guild, [activity.name])
                    if len(new_games) > 0:
                        game = list(new_games.values())[0]

                        original_message = f"Hey, guys! Looks like some folks have started playing a new game, <@&{game['role']}>!\n*```yaml\n{game['summary']}```*"
                        view = PageView(original_message, ListType.Select_Game, [new_games], None, 1, current.guild)
                        # TODO: CHANGE test_channel to general_channel
                        view.message = await test_channel.send(original_message + "\nGo ahead and click the button below to add yourself to the role!", view = view, files = await GetImages(new_games))
                    elif len(already_exists) > 0:
                        game = list(already_exists.values())[0]
                    else:
                        await AddAlias(self.bot, current.guild, activity.name, current)
                        return
                    
                # Log game activity for server stats
                StartPlayingGame(current, game['name'])

                # Exits if member opted out of getting notifications
                if member['opt_out']:
                    return

                # Exit if the member doesn't want to be bothered about this game
                if game['name'] in member['games'] and member['games'][game['name']]['tracked'] == False:
                    return
                
                # Get the role associated with the current activity name (game name)
                role = current.guild.get_role(game['role'])
                
                # When somebody starts playing a game and if they are part of the role
                if role in current.roles and game['name'] in member['games']: 
                    await admin_channel.send(f"`{member['display_name']}` started playing `{activity.name}`!")
                else:
                    # Informs the admin channel that the member is playing a game without it's role assigned
                    await admin_channel.send(f"`{member['display_name']}` started playing `{activity.name}` and/or does not have the role or is not being tracked!")

                    # Get the direct message channel from the member
                    dm_channel = await current.create_dm()

                    # Setup original message
                    original_message = f"Hey, {member['display_name']}! I'm from the [Pavilion Horde Server]({config['Links']['GeneralChannel']}) and I noticed you were playing `{activity.name}` and don't have the role assigned!"
                    
                    # Populate view and send direct message
                    view = DirectMessageView(original_message, role, current, game)
                    view.message = await dm_channel.send(f"{original_message} Would you like me to add you to it so you'll be notified when someone is looking for a friend?", view = view, files = await GetImages({game['name'] : game}))
        
        # else:
        #     # Do not continue if neither previous or current activity type is playing
        #     if previous.activity and previous.activity.type != discord.ActivityType.playing:
        #         if current.activity and current.activity.type != discord.ActivityType.playing:
        #             return

        #     # Gather member information
        #     member_display_name = current.display_name.encode().decode('ascii','ignore')

        #     # Exits if the member is a bot or isn't whitelisted
        #     if config['WhitelistEnabled'] and current.bot or current.name not in config['WhitelistMembers']:
        #         return
            
        #     # Adds member to members dictionary for potential tracking (will ask if they want to opt-out)
        #     if current.name not in members:
        #         AddMember(current)

        #     # Assigns member with current.name
        #     member = members[current.name]

        #     # If there's a previous activity and it exists in games, someone stopped playing the game
        #     if previous.activity and (previous.activity.name in games or previous.activity.name in aliases):
        #         StopPlayingGame(current, previous.activity.name)

        #         # Exit if there's no new activity or if the new activity is in the blacklist
        #         if current.activity is None or current.activity.name in config['ActivityBlacklist']:
        #             return
            
        #     # Exits if there's a previous activity and it's the same as the current activity (prevents duplicate checks)
        #     if previous.activity and current.activity and previous.activity.name == current.activity.name:
        #         return
            
        #     # Continues if there's a current activity and if it's not in the blacklist
        #     if current.activity and current.activity.name not in config['ActivityBlacklist']:            
        #         # Exit if the member has opted out of the autoroler
        #         if member['opt_out']:
        #             return
                
        #         # Checks of the activity is an alias first to avoid a potentially unnecessary API call
        #         if current.activity.name in aliases:
        #             game_name = aliases[current.activity.name]
        #             if game_name in games:
        #                 game = games[game_name]
        #             else:
        #                 await admin_channel.send(f"`{member['display_name']}` started playing `{current.activity.name}`, and I found an alias with that name, but the game associated with it isn't in the list! Not sure how that happened!")
        #                 return
        #         else:
        #             # If there isn't a game recorded for the current activity already, add it
        #             new_games, already_exists, failed_to_find = await AddGames(current.guild, [current.activity.name])
        #             if len(new_games) > 0:
        #                 game = list(new_games.values())[0]

        #                 original_message = f"Hey, guys! Looks like some folks have started playing a new game, <@&{game['role']}>!\n*```yaml\n{game['summary']}```*"
        #                 view = PageView(original_message, ListType.Select_Game, [new_games], None, 1, current.guild)
        #                 view.message = await general_channel.send(original_message + "\nGo ahead and click the button below to add yourself to the role!", view = view, files = await GetImages(new_games))
        #             elif len(already_exists) > 0:
        #                 game = list(already_exists.values())[0]
        #             else:
        #                 await AddAlias(self.bot, current.guild, current.activity.name, current)
        #                 return
                    
        #         # Log game activity for server stats
        #         StartPlayingGame(current, game['name'])

        #         # Get the role associated with the current activity name (game name)
        #         role = current.guild.get_role(game['role'])
                
        #         # Exit if the member doesn't want to be bothered about this game
        #         if role.name in member['games'] and not member['games'][role.name]['tracked']:
        #             return
                
        #         # When somebody starts playing a game and if they are part of the role
        #         if role in current.roles and role.name in member['games']: 
        #             await admin_channel.send(f"`{member['display_name']}` started playing `{game['name']}`!")
        #         else:
        #             # Informs the test channel that the member is playing a game without it's role assigned
        #             await admin_channel.send(f"`{member['display_name']}` started playing `{game['name']}` and/or does not have the role or is not being tracked!")

        #             # Get the direct message channel from the member
        #             dm_channel = await current.create_dm()

        #             # Setup original message
        #             original_message = f"Hey, `{member['display_name']}`! I'm from the [Pavilion Horde Server]({config['Links']['GeneralChannel']}) and I noticed you were playing `{game['name']}` and don't have the role assigned!"
                    
        #             # Populate view and send direct message
        #             view = DirectMessageView(original_message, role, current, game)
        #             view.message = await dm_channel.send(f"{original_message} Would you like me to add you to it so you'll be notified when someone is looking for a friend?", view = view, files = await GetImages({game['name'] : game}))
    
    @commands.command()
    async def opt_in(self, ctx):
        """Allows a member to opt back in to tracking their activity"""
        # Get member that sent the command
        member = ctx.message.author

        # Updates the out_out flag for the member
        update = {'opt_out' : False}
        UpdateMember(member, update)
        await ctx.reply(f"I've opted you back in for automatic role assignments! If in the future you'd like to opt back out, simply use the `!opt_out` command anywhere in the server!")

    @commands.command()
    async def opt_out(self, ctx,):
        """Allows a member to opt out of tracking their activity"""
        # Get member that sent the command
        member = ctx.message.author

        # Updates the out_out flag for the member
        update = {'opt_out' : True}
        UpdateMember(member, update)
        await ctx.reply(f"I've opted you out of the automatic role assignment! If in the future you'd like to opt back in, simply use the `!opt_in` command anywhere in the server!")

    @commands.command()
    async def list_games(self, ctx, *, list_filter = None):
        """Returns a list of game pages from the server."""
        # Get member that sent the command
        member = ctx.message.author
        guild  = ctx.guild

        # List the games if there are more than zero. Otherwise reply with a passive agressive comment
        if len(games) > 0:
            # Convert a long list of games into sets of 25 or less
            list_sets = GetListSets(games, 20, list_filter, SortType.Alphabetical)
            if not list_sets:
                await ctx.reply(f"Could not find any games similar to `{list_filter}`")
            else:
                original_message = f"Here's your game list, {member.mention}!"
                view = PageView(original_message, ListType.Select_Game, list_sets, list_filter, 1, guild, member)
                view.message = await ctx.reply(f"{original_message}\n*`{SortType.Alphabetical.value}: (Page 1 of {len(list_sets)})` Please select the games that you're interested in playing:*", view = view)
        else:
            await ctx.reply("This is where I would list my games... IF I HAD ANY!")

    @commands.command()
    async def add_games(self, ctx, *, arg):
        """Manually adds a game or a set of games (max 10) to the autoroler.\nSeperate games using commas: !add_games game_1, game_2, ..., game_10"""
        # Get member that sent the command
        member = ctx.message.author

        # Splits the provided arg into a list of games
        all_games = [game for game in arg.split(',')][:10]

        # Attempt to add the games provided, returning new, existing, and/or failed to add games
        new_games, already_exists, failed_to_find = await AddGames(ctx.guild, all_games)

        # Respond in one of the 8 unique ways based on the types of games trying to be added
        if len(new_games) == 0 and len(already_exists) == 0 and len(failed_to_find) == 0:
            await ctx.reply(f"{member.mention}, you need to actually tell me what you want to add")

        elif len(new_games) == 0 and len(already_exists) == 0 and len(failed_to_find) > 0:
            await ctx.reply(f"I don't recognize any of these games, {member.mention}. Are you sure you know what you're talking about?")

        elif len(new_games) == 0 and len(already_exists) > 0 and len(failed_to_find) == 0:
            original_message = f"I already have all of these recorded! {member.mention}, how about you do a little more research before asking questions."
            view = PageView(original_message, ListType.Select_Game, [already_exists], None, 1, ctx.guild)
            view.message = await ctx.reply(original_message, view = view)

        elif len(new_games) == 0 and len(already_exists) > 0 and len(failed_to_find) > 0:
            original_message = f"Thanks for the contribution, {member.mention}! I already have {GetNames(already_exists)}, but I don't recognize {GetNames(failed_to_find)}."
            view = PageView(original_message, ListType.Select_Game, [already_exists], None, 1, ctx.guild)
            view.message = await ctx.reply(original_message, view = view)

        elif len(new_games) > 0 and len(already_exists) == 0 and len(failed_to_find) == 0:
            original_message = f"Thanks for the contribution, {member.mention}! I've added {GetRoles(new_games)} to the list of games!\n*Please select any of the games you're interested in playing below*"
            view = PageView(original_message, ListType.Select_Game, [new_games], None, 1, ctx.guild)
            view.message = await ctx.reply(original_message, view = view, files = await GetImages(new_games))
            
        elif len(new_games) > 0 and len(already_exists) == 0 and len(failed_to_find) > 0:
            original_message = f"Thanks for the contribution, {member.mention}! I've added {GetRoles(new_games)} to the list of games! But I don't recognize {GetNames(failed_to_find)}.\n*Please select any of the games you're interested in playing below*"
            view = PageView(original_message, ListType.Select_Game, [new_games], None, 1, ctx.guild)
            view.message = await ctx.reply(original_message, view = view, files = await GetImages(new_games))
            
        elif len(new_games) > 0 and len(already_exists) > 0 and len(failed_to_find) == 0:
            original_message = f"Thanks for the contribution, {member.mention}! I've added {GetRoles(new_games)} to the list of games! I already have {GetNames(already_exists)}.\n*Please select any of the games you're interested in playing below*"
            view = PageView(original_message, ListType.Select_Game, [new_games | already_exists], None, 1, ctx.guild)
            view.message = await ctx.reply(original_message, view = view, files = await GetImages(new_games))
            
        elif len(new_games) > 0 and len(already_exists) > 0 and len(failed_to_find) > 0:
            original_message = f"Thanks for the contribution, {member.mention}! I've added {GetRoles(new_games)} to the list of games! I already have {GetNames(already_exists)}, but I don't recognize {GetNames(failed_to_find)}.\n*Please select any of the games you're interested in playing below*"
            view = PageView(original_message, ListType.Select_Game, [new_games | already_exists], None, 1, ctx.guild)
            view.message = await ctx.reply(original_message, view = view, files = await GetImages(new_games))

    @commands.command()
    async def remove_games(self, ctx, *, list_filter = None):
        """Returns a list of games that can be selected for removal."""
        # Get member that sent the command
        member: discord.Member = ctx.message.author
        guild: discord.Guild = ctx.message.guild

        # Exits if the member is not an admin
        role: discord.Role = guild.get_role(config['AdminRole'])
        if role and role.name != "deleted-role":
            if role not in member.roles:
                await ctx.reply(f"Sorry, {member.mention}, I was unable to complete your request. You need to be part of the <@&{config['AdminRole']}> role to add aliases!")
                return
        else:
            await ctx.reply(f"Sorry, {member.mention}, I was unable to complete your request. I was unable to find the role `ID:{config['AdminRole']}` - I'm, therefore, unable to verify your admin rights!")
            return
        
        # Lists the games to remove if there's more than zero. Otherwise reply with a passive agressive comment
        if len(games) > 0:
            # Convert a long list of games into sets of 25 or less
            list_sets = GetListSets(games, 20, list_filter, SortType.Alphabetical)
            
            if not list_sets:
                await ctx.reply(f"Could not find any games similar to `{list_filter}`")
            else:
                original_message = f"Here you go, {member.mention}!"
                view = PageView(original_message, ListType.Remove_Game, list_sets, list_filter, 1, guild, member)
                view.message = await ctx.reply(f"{original_message}\n*`{SortType.Alphabetical.value}: (Page 1 of {len(list_sets)})` Please select the game(s) you'd like to remove...*", view = view)
        else:
            await ctx.reply("This is where I would list my games... IF I HAD ANY!")

    @commands.command()
    async def list_aliases(self, ctx):
        """Returns a list of aliases from the server."""
        if len(aliases) > 0:
            # Get's the longest alias for formatting
            longest_alias = max(list(aliases.keys()), key=len)

            # Sets up the message to reply with
            message = "__**Here's that list of game aliases you asked for!**__\n"
            for alias, game in aliases.items():
                message += f"`{alias.ljust(len(longest_alias))}` : `{game}`\n"

            # Replies with the message
            await ctx.reply(message)
        else:
            await ctx.reply("This is where I would list my aliases... IF I HAD ANY!")
    
    @commands.command()
    async def add_alias(self, ctx, *, arg):
        """Adds the provided alias to the server."""
        # Get member that sent the command
        member: discord.Member = ctx.message.author
        guild: discord.Guild = ctx.message.guild

        # Exits if the member is not an admin
        role = guild.get_role(config['AdminRole'])
        if role:
            if role not in member.roles:
                await ctx.reply(f"Sorry, {member.mention}, I was unable to complete your request. You need to be part of the <@&{config['AdminRole']}> role to add aliases!")
                return
        else:
            await ctx.reply(f"Sorry, {member.mention}, I was unable to complete your request. I was unable to find the role `ID:{config['AdminRole']}` - I'm, therefore, unable to verify your admin rights!")
            return
        
        await AddAlias(self.bot, ctx.guild, arg)

    @commands.command()
    async def remove_aliases(self, ctx, *, list_filter = None):
        """Returns a list of aliases that can be selected for removal."""
        # Get member that sent the command
        member: discord.Member = ctx.message.author
        guild: discord.Guild = ctx.message.guild

        # Exits if the member is not an admin
        role = guild.get_role(config['AdminRole'])
        if role:
            if role not in member.roles:
                await ctx.reply(f"Sorry, {member.mention}, I was unable to complete your request. You need to be part of the <@&{config['AdminRole']}> role to add aliases!")
                return
        else:
            await ctx.reply(f"Sorry, {member.mention}, I was unable to complete your request. I was unable to find the role `ID:{config['AdminRole']}` - I'm, therefore, unable to verify your admin rights!")
            return
        
        if len(aliases) > 0:
            # Convert a long list of games into sets of 25 or less
            list_sets = GetListSets(aliases, 20, list_filter, SortType.Alphabetical)
            
            if not list_sets:
                await ctx.reply(f"Could not find any aliases similar to `{list_filter}`")
            else:
                original_message = f"Here you go, {member.mention}!"
                view = PageView(original_message, ListType.Remove_Alias, list_sets, list_filter, 1, guild, member)
                view.message = await ctx.reply(f"{original_message}\n*`{SortType.Alphabetical.value}: (Page 1 of {len(list_sets)})` Please select the aliases you'd like to remove...*", view = view)
        else:
            await ctx.reply("This is where I would list my aliases... IF I HAD ANY!")

    @commands.command()
    async def top_games(self, ctx):
        '''Returns the top 5 games played in the server or by yourself.'''
        original_message = f"Hey, {ctx.message.author.mention}! Would you like to see the top games for the server or just yourself?"
        view = PlaytimeView(original_message, ctx.message.author)
        view.message = await ctx.reply(f"{original_message}", view = view)