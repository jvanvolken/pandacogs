
import requests
import discord
import difflib
import string
import math
import json
import os

from datetime import datetime, timedelta
from redbot.core import commands
from threading import Timer
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

# List types
class Flags(Enum):
    Games  = 1
    Members  = 2
    Aliases = 3

# Cog Directory in Appdata
docker_cog_path  = "/data/cogs/AutoRolerPro"
games_file       = f"{docker_cog_path}/games.json"
members_file     = f"{docker_cog_path}/members.json"
aliases_file     = f"{docker_cog_path}/aliases.json"
log_file         = f"{docker_cog_path}/log.txt"

# Channel Links
general_channel_link = "https://discord.com/channels/633799810700410880/633799810700410882"

# Bot Channel
bot_channel_id = 634197647787556864
admin_channel_id = 1013251079418421248
test_channel_id = 665572348350693406

# Blacklist for member activities
activity_blacklist = ["Spotify"]

# Instantiates IGDB wrapper
# curl -X POST "https://id.twitch.tv/oauth2/token?client_id=CLIENT_ID&client_secret=CLIENT_SECRET&grant_type=client_credentials"
db_header = {
    'Client-ID': 'fqwgh1wot9cg7nqu8wsfuzw01lsln9',
    'Authorization': 'Bearer 9csdv9i9a61vpschjcdcsfm4nblpyq'
}

# Dictionary of updated file flags
update_flags = {
    Flags.Games: {'status': False, 'comment': ""}, 
    Flags.Members: {'status': False, 'comment': ""}, 
    Flags.Aliases: {'status': False, 'comment': ""}
}

# Sets the default max attempts to set an alias
alias_max_attempts = 5

# Sets the default backup frequency (hours)
backup_frequency = 0.1

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

# Initializes the aliases list
if os.path.isfile(aliases_file):
    with open(aliases_file, "r") as fp:
        aliases = json.load(fp)
else:
    aliases = {}
    with open(aliases_file, "w") as fp:
        json.dump(aliases, fp, indent = 2, default = str)


def UpdateFlag(flag: Flags, status: bool = False, comment: str = ""):
    # Stores a temp flags
    temp_flag = update_flags[flag]

    # Updates the flag
    update_flags[flag] = {'status': status, 'comment': f"{comment}\n{temp_flag['comment']}"}

    if temp_flag['status']:
        return temp_flag['comment']
    else:
        return None

def Log(message):
    # Initializes the members list
    if os.path.isfile(log_file):
        file = open(log_file, "w")
    else:
        # Append-adds at last
        file = open(log_file, "a")

    file.writelines(message)
    file.close()

# Sets up the non-blocking data backup routine in accordance with the backup frequency
def BackupRoutine():
    # Sets up the next backup routine
    Timer(backup_frequency * 3600, BackupRoutine).start()

    # Logs the current date and time
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    Log(f"{current_datetime}: Initiating routine data backup sequence.")

    # Returns true if games flag is updated
    comment = UpdateFlag(Flags.Games)
    if comment:
        with open(games_file, "w") as fp:
            json.dump(games, fp, indent = 2, default = str)        
        
        # Logs backup
        Log(f"{current_datetime}: Successfully saved to {games_file}\n--{comment}")

    # Returns true if members flag is updated
    comment = UpdateFlag(Flags.Members)
    if comment:
        with open(members_file, "w") as fp:
            json.dump(members, fp, indent = 2, default = str)
        
        # Logs backup
        Log(f"{current_datetime}: Successfully saved to {members_file}\n--{comment}")

    # Returns true if aliases flag is updated
    comment = UpdateFlag(Flags.Aliases)
    if comment:
        with open(aliases_file, "w") as fp:
            json.dump(aliases, fp, indent = 2, default = str)
        
        # Logs backup
        Log(f"{current_datetime}: Successfully saved to {aliases_file}\n--{comment}")

Timer(backup_frequency * 3600, BackupRoutine).start()

# Returns a string list of game names
def GetNames(game_list: list):
    names = []
    for game in game_list.values():
        names.append(game['name'])
    return f"`{'`, `'.join(names)}`"

# Returns a list of image files
async def GetImages(game_list: list):
    images = []
    for game in game_list.values():
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
def GetListSets(game_list: dict, set_amount: int):
    list_sets = []
    item_count = 0
    for name, details in game_list.items():
        idx = math.floor(item_count/set_amount)
        if idx < len(list_sets):
            list_sets[idx][name] = details
        else:
            list_sets.append({})
            list_sets[idx][name] = details
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
    for detail in ['name', 'display_name', 'created_at', 'joined_at', 'roles']:
        if hasattr(member, detail):
            member_details[detail] = getattr(member, detail)

    member_details['games'] = {}
    member_details['opt_out'] = False
    
    # Adds the member details to the members list
    members[member_details['name']] = member_details

    # Toggles the updated flag for members
    UpdateFlag(Flags.Members, True, f"Added a new member, {member.name}")

    # Saves the members dictionary to the json file
    # with open(members_file, "w") as fp:
    #     json.dump(members, fp, indent = 2, default = str)

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
    # Updates specific member with new details
    MergeDictionaries(members[member.name], new_details)
    
    # Toggles the updated flag for members
    UpdateFlag(Flags.Members, True, f"Updated a member, {member.name}")
    # Saves the members dictionary to the json file
    # with open(members_file, "w") as fp:
    #     json.dump(members, fp, indent = 2, default = str)

# Removes game from games list and saves to file
async def RemoveGame(role: discord.Role, game_name: str):
    if game_name in games:
        # role = discord.utils.get(guild.roles, name = game_name) #TODO: Shouldn't need this anymore after replacing guild with role reference
        if role:
            await role.delete()
        else:
            print(f"Failed to remove game. Could not find this role: `{game_name}`!")

        del games[game_name]

        # Toggles the updated flag for games
        UpdateFlag(Flags.Games, True, f"Removed a game, {game_name}")

        # with open(games_file, "w") as fp:
        #     json.dump(games, fp, indent = 2, default = str)
        
        return True
    else:
        print(f"Failed to remove game. Could not find {game_name} in list.")
        return False

# Adds a list of games to the games list after verifying they are real games
async def AddGames(guild: discord.Guild, game_list: list):
    new_games      = {}
    already_exists = {}
    failed_to_find = {}
    for game in game_list:
        game = string.capwords(game)

        # TODO: Check existing games first to prevent a potentially unnecessary API call
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
            if "role" not in games[latest_game['name']]:
                # Looks for an existing role for the game
                role = discord.utils.get(guild.roles, name = latest_game['name'])
                if role:
                    # Stores the role for future use
                    games[latest_game['name']]['role'] = role.id

                    # Toggles the updated flag for games
                    UpdateFlag(Flags.Games, True, f"Added missing role entry for the {latest_game['name']} game!")

                    # Update game in game list and saves file
                    # with open(games_file, "w") as fp:
                    #     json.dump(games, fp, indent = 2, default = str)

            already_exists[latest_game['name']] = games[latest_game['name']]
        elif latest_game: 
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
            UpdateFlag(Flags.Games, True, f"Added new game and role to server, {latest_game['name']}")
            # with open(games_file, "w") as fp:
            #     json.dump(games, fp, indent = 2, default = str)
        else:
            failed_to_find[game] = {'name' : game, 'summary' : 'unknown', 'rating' : 0, 'first_release_date' : 'unknown'}
        
    return new_games, already_exists, failed_to_find

# Adds an alias and game to the aliases list, adds the game if it doesn't already exist
async def AddAlias(bot: discord.Client, guild: discord.Guild, alias: str, member: discord.Member = None):
    admin_channel = guild.get_channel(admin_channel_id)
    test_channel = guild.get_channel(test_channel_id)

    # Send the original message
    if member:
        original_message = await admin_channel.send(f"{member.mention} started playing `{alias}`, but I can't find it in the database!\n*Please reply with the full name associated with this game!*")
    else:
        original_message = await test_channel.send(f"So you want to set up `{alias}` as an alias, huh? Reply with the full name of the game associated with this alias!")

    # Sets up a loop to allow for multiple attempts at setting a name
    game = None
    attempt_count = 0
    while not game and attempt_count < alias_max_attempts:
        # Returns true of the message is a reply to the original message
        def check(message):
            return message.reference and message.reference.message_id == original_message.id

        # Wait for a reply in accordance with the check function
        msg = await bot.wait_for('message', check = check)
        
        # Add the msg.content as a game to the server
        new_games, already_exists, failed_to_find = await AddGames(guild, [msg.content])

        remaining_attempts = alias_max_attempts - attempt_count - 1

        # If a new or existing game is found, assign it to game to exit the loop
        if len(new_games) > 0:
            game = list(new_games.values())[0]
        elif len(already_exists) > 0:
            game = list(already_exists.values())[0]
        elif len(failed_to_find) > 0 and remaining_attempts > 0:
            original_message = await msg.reply(f"I was unable to assign `{alias}` to a game - I couldn't find `{msg.content}` in the database!\n*Please try again by replying to this message! Attempts remaining: {remaining_attempts}*")
            attempt_count += 1
    
    if game:
        aliases[alias] = game['name']

        # Toggles the updated flag for aliases
        UpdateFlag(Flags.Aliases, True, f"Assigned a new alias, {alias}, to the {game['name']} game!")
        # Saves the members dictionary to the json file
        # with open(aliases_file, "w") as fp:
        #     json.dump(aliases, fp, indent = 2, default = str)

        # Once a game is found, it sets the alias and exits
        await msg.reply(f"Thanks, {msg.author.mention}! I've given <@&{game['role']}> an alias of `{alias}`.", files = await GetImages({game['name'] : game}))
    else:
        await msg.reply(f"Thanks for the attempt, {msg.author.mention}, but I wasn't able to find any games to assign the alias `{alias}` to!\n*Try again with `!set_alias {alias}`*")

# Removes a specific alias from the aliases list
def RemoveAlias(alias_name: str):
    if alias_name in aliases:
        del aliases[alias_name]

        # Toggles the updated flag for aliases
        UpdateFlag(Flags.Aliases, True, f"Removed the {alias_name} alias.")
        # with open(aliases_file, "w") as fp:
        #     json.dump(aliases, fp, indent = 2, default = str)

        return True 
    else:
        return False

# Handles tracking of gameplay when someone starts playing
def StartPlayingGame(member: discord.Member, game_name: str):
    # Checks of game_name is an alias; if not and game_name is also not in games, return and log failure
    if game_name in aliases:
        game_name = aliases[game_name]
    elif game_name not in games:
        print(f"Could not find {game_name} in the game list or aliases when {member} started playing!")
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
    games[game_name]['history'][date][member.name]['last_played'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

    # Toggles the updated flag for games
    UpdateFlag(Flags.Games, True, f"{member.name} started playing {game_name}")
    # Saves the changes to the games_file
    # with open(games_file, "w") as fp:
        # json.dump(games, fp, indent = 2, default = str)

# Records number of hours played since member started playing game and tallies for the day
def StopPlayingGame(member: discord.Member, game_name: str):
    # Checks of game_name is an alias; if not and game_name is also not in games, return and log failure
    if game_name in aliases:
        game_name = aliases[game_name]
    elif game_name not in games:
        print(f"Could not find {game_name} in the game list or aliases when {member} stopped playing!")
        return
    
    # Grabs the current YYYY-MM-DD from the current datetime
    date = datetime.now().strftime('%Y-%m-%d')

    # Constructs history dictionary for game if missing
    if 'history' in games[game_name] and date in games[game_name]['history'] and member.name in games[game_name]['history'][date]:
        # Get the difference in time between last_played and now
        last_played  = games[game_name]['history'][date][member.name]['last_played']
        delta_time = datetime.now() - datetime.strptime(last_played, '%Y-%m-%d %H:%M:%S.%f')

        # TODO: Compare now date with last_played date, if now is next day, split hours between the two days

        # Convert delta_time to hours and round to 2 decimal places
        hours = round(delta_time.total_seconds()/3600, 2)

        # Adds the member to the current date if missing
        if 'playtime' not in games[game_name]['history'][date][member.name]:
            games[game_name]['history'][date][member.name]['playtime'] = 0
        
        games[game_name]['history'][date][member.name]['playtime'] = round(games[game_name]['history'][date][member.name]['playtime'] + hours, 2)

        # Toggles the updated flag for games
        UpdateFlag(Flags.Games, True, f"{member.name} stopped playing {game_name}")
        # Saves the changes to the games_file
        # with open(games_file, "w") as fp:
        #     json.dump(games, fp, indent = 2, default = str)
    else:
        print(f"Something went wrong when {member} stopped playing {game_name}!")

# Gets the total playtime over the last number of given days. Include optional member to filter
def GetPlaytime(game_list: dict, days: int, count: int, member: discord.Member = None):
    top_games = {}
    for game_name, game_value in game_list.items():
        # Skips game if there's not history
        if 'history' not in game_value:
            continue
        
        # Initializes the gameplay dictionary with zeros for each game
        top_games[game_name] = 0
        for day, day_value in game_value['history'].items():
            # Checks if day is within the number of days specified
            if datetime.strptime(day, '%Y-%m-%d') > datetime.now() - timedelta(days = days):
                for name, details in day_value.items():
                    # If member is provided, filter by their name
                    if member == None or name == member.name:
                        top_games[game_name] += details['playtime']
        
        # Delete game_name from top_games if it's zero
        if top_games[game_name] == 0:
            del top_games[game_name]
        else:
            top_games[game_name] = round(top_games[game_name], 2)

    # Sort the list by highest hours played and shrink to count
    sorted_list = sorted(top_games.items(), key = lambda x:x[1], reverse=True)[:count]
    return dict(sorted_list)

# Create a class called DirectMessageView that subclasses discord.ui.View
class DirectMessageView(discord.ui.View):
    def __init__(self, original_message, role, member):
        super().__init__(timeout = 60 * 60 * 12) # Times out after 12 hours

        self.original_message = original_message
        self.role = role
        self.member = member

        self.add_item(self.YesButton(self.original_message, self.role, self.member))
        self.add_item(self.NoButton(self.original_message, self.role, self.member))
        self.add_item(self.OptOutButton(self.original_message, self.role, self.member))

    # Create a class called YesButton that subclasses discord.ui.Button
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
                
                # TODO: Only assigning tracked when responding here, need to also toggle tracked when interfacing with !list_games
                # Records answer for this game and the current datetime for last played
                update = {'games' : {self.role.name : {'name' : self.role.name, 'tracked' : True, 'last_played' : datetime.now()}}}
                UpdateMember(self.member, update)

                # Responds to the request
                await interaction.message.edit(content = f"{self.original_message}\n*You've selected `YES`*", view = None)
                await interaction.response.send_message(f"Awesome! I've added you to the `{self.role.name}` role! Go ahead and mention the role in the [server]({general_channel_link}) to meet some new friends!")
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, something went wrong! I was unable to assign the `{self.role.name}` role to you. Please check the logs for further details.")
                raise Exception(error)
                
    # Create a class called NoButton that subclasses discord.ui.Button             
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
                UpdateMember(self.member, update)
                
                await interaction.message.edit(content = f"{self.original_message}\n*You've selected `NO`*", view = None)
                await interaction.response.send_message(f"Understood! I won't ask about `{self.role.name}` again! Feel free to manually add yourself anytime using the `!list_games` command in the [server]({general_channel_link})!")
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, I was unable to complete the requested command! Please check the logs for further details.")
                raise Exception(error)
              
    # Create a class called OptOutButton that subclasses discord.ui.Button                   
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
                UpdateMember(self.member, update)

                await interaction.message.edit(content = f"{self.original_message}\n*You've selected `OPT OUT`*", view = None)
                await interaction.response.send_message(f"Sorry to bother! I've opted you out of the automatic role assignment! If in the future you'd like to opt back in, simply use the `!opt_in` command anywhere in the [server]({general_channel_link})!")
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, I was unable to complete the requested command! Please check the logs for further details.")
                raise Exception(error)

    async def on_timeout(self):
        #TODO Make this edit dynamic based on what the user selected (or didn't)
        await self.message.edit(content = f"{self.original_message}\n*This request has timed out! If you didn't get to this already, you can still add youself to the roll manually by using the command `!list_games` in the [server]({general_channel_link})!*", view = None)

# Create a class called ListView that subclasses discord.ui.View
class ListView(discord.ui.View):
    def __init__(self, original_message: str, list_type: ListType, list_items: dict, guild: discord.Guild, member: discord.Member = None):
        super().__init__(timeout = 60 * 60 * 12) # Times out after 12 hours 

        self.original_message = original_message
        self.list_type = list_type
        self.list_items = list_items
        self.guild = guild
        self.member = member

        for name, details in self.list_items.items():
            self.add_item(self.ListButton(self.original_message, name, details, self.list_type, self.list_items, self.guild, self.member))

    # Create a class called ListButton that subclasses discord.ui.Button
    class ListButton(discord.ui.Button):
        def __init__(self, original_message: str, name: str, details: dict, list_type: ListType, list_items: dict, guild: discord.Guild, member: discord.Member = None):
            # Set object variables
            self.name = name
            self.details = details
            self.list_type = list_type
            self.list_items = list_items
            self.original_message = original_message
            self.guild = guild
            self.member = member
            self.role = self.guild.get_role(self.details['role'])
            
            # Check if message author has the role and change button color accordingly
            if self.member:
                if self.role in self.member.roles:
                    button_style = discord.ButtonStyle.success
                else:
                    button_style = discord.ButtonStyle.secondary
            else:
                button_style = discord.ButtonStyle.primary

            # Get all server emojis
            emojis = self.guild.emojis

            # Get the closest matching emoji to game name
            emoji_names = [emoji.name for emoji in emojis]
            match = difflib.get_close_matches(self.name.lower(), emoji_names, 1)

            # Return the actual emoji from name
            emoji = None
            if match:
                for option in emojis:
                    if option.name == match[0]:
                        emoji = option
                        break

            # Setup buttom
            super().__init__(label = self.name, style = button_style, emoji = emoji)

        async def callback(self, interaction):
            if self.member and self.member != interaction.user:
                extra_comment = ""
                if self.list_type is ListType.Select_Game:
                    extra_comment = "Please use !list_games to interact!"
                    
                await interaction.response.send_message(f"You're not {self.member.mention}! Who are you?\n*{extra_comment}*", ephemeral = True, delete_after = 10)
                return
            
            if self.list_type is ListType.Select_Game:
                # Looks for the role with the same name as the game
                if self.role:
                    if self.role in interaction.user.roles:
                        # Assign role to member
                        member = interaction.user
                        await member.remove_roles(self.role)

                        view = ListView(self.original_message, ListType.Select_Game, self.list_items, self.guild, self.member)
                        view.message = await interaction.message.edit(view = view)

                        await interaction.response.send_message(f"I have removed you from the `{self.name}` role!", ephemeral = True, delete_after = 10)
                    else:
                        # Assign role to member
                        member = interaction.user
                        await member.add_roles(self.role)

                        view = ListView(self.original_message, ListType.Select_Game, self.list_items, self.guild, self.member)
                        view.message = await interaction.message.edit(view = view)

                        # Informs the user that the role has been assigned to them
                        await interaction.response.send_message(f"Added you to the `{self.name}` role!", ephemeral = True, delete_after = 10)
                else:
                    await interaction.response.send_message(f"Something went wrong, I can't find the associated role for `{self.name}`.\nPlease try adding the game again using !add_games {self.name}", ephemeral = True)

            elif self.list_type is ListType.Remove_Game:
                # Tries to remove the game, returns false if it fails
                if await RemoveGame(self.role, self.name):
                    del self.list_items[self.name]

                    view = ListView(self.original_message, ListType.Remove_Game, self.list_items, self.guild, self.member)
                    view.message = await interaction.message.edit(view = view)

                    await interaction.response.send_message(f"I have removed {self.name} from the list!", ephemeral = True, delete_after = 10)
                else:
                    await interaction.response.send_message(f"I couldn't removed {self.name} from the list!\n*Check out the log for more details!*", ephemeral = True, delete_after = 10)

            elif self.list_type is ListType.Remove_Alias:
                # Tries to remove the alias, returns false if it fails
                if RemoveAlias(self.name):
                    await interaction.response.send_message(f"`{self.name}` has been removed from the list!")
                else:
                    await interaction.response.send_message(f"Unable to remove `{self.name}` - I could not find it in the list of aliases!")

    async def on_timeout(self):
        if not self.original_message:
            await self.message.delete()
        else:
            if self.member:
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
        self.add_item(self.SelfButton(self.original_message, self.member))

    # Create a class called YesButton that subclasses discord.ui.Button
    class ServerButton(discord.ui.Button):
        def __init__(self, original_message: str, member: discord.Member):
            super().__init__(label = "Server", style = discord.ButtonStyle.secondary, emoji = "💻")
            self.original_message = original_message
            self.member = member

        async def callback(self, interaction):
            try:
                playtime_message = ""
                for game, hours in GetPlaytime(games, 30, 5).items():
                    playtime_message += f"- **{game}** *({hours:,} hours)*\n"

                await interaction.response.send_message(f"Check out this server's top 5 games this month!\n{playtime_message}")
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, something went wrong! I was unable to grab the server's top 5 games for this month. Please check the logs for further details.", ephemeral = True)
                raise Exception(error)

    class SelfButton(discord.ui.Button):
        def __init__(self, original_message: str, member: discord.Member):
            super().__init__(label = "Self", style = discord.ButtonStyle.secondary, emoji = "😁")
            self.original_message = original_message
            self.member = member

        async def callback(self, interaction):
            try:
                playtime_message = ""
                for game, hours in GetPlaytime(games, 30, 5, self.member).items():
                    playtime_message += f"- **{game}** *({hours:,} hours)*\n"

                await interaction.response.send_message(f"Here you go, {self.member.mention}! These are your top 5 games this month!\n{playtime_message}", ephemeral = True)
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, something went wrong! I was unabe to grab your top 5 games for this month. Please check the logs for further details.", ephemeral = True)
                raise Exception(error)
            
    async def on_timeout(self):
        await self.message.edit(content = f"{self.original_message}\n*This request has timed out! If you hadn't finished, please try again!*", view = None)

class AutoRolerPro(commands.Cog):
    """My custom cog"""
    def __init__(self, bot):
        self.bot = bot

    # Detect when a member's presence changes
    @commands.Cog.listener(name='on_presence_update')
    async def on_presence_update(self, previous: discord.Member, current: discord.Member):
        # Get important information about the context of the event
        bot_channel = current.guild.get_channel(bot_channel_id)
        admin_channel = current.guild.get_channel(admin_channel_id)
        test_channel = current.guild.get_channel(test_channel_id)

        # Gather member information
        member_display_name = current.display_name.encode().decode('ascii','ignore')

        # Exits if the member is a bot or isn't whitelisted
        if current.bot or current.name not in ["sad.panda.", "agvv20", "ashlore.", "malicant999", "goldifish"]:
            return
        
        # Exit if there's not current activity
        if current.activity is None:
            if previous.activity and previous.activity.name in games:
                StopPlayingGame(current, previous.activity.name)
            return
        
        # Adds member to members dictionary for potential tracking (will ask if they want to opt-out)
        if current.name not in members:
            AddMember(current)

        # Assigns member with current.name
        member = members[current.name]

        # Exits if there's a previous activity and it's the same as the current activity (prevents duplicate checks)
        if previous.activity and previous.activity.name == current.activity.name:
            return
        
        # Continues if there's a current activity and if it's not in the blacklist
        if current.activity and current.activity.name not in activity_blacklist:
            # Log game activity for server stats
            StartPlayingGame(current, current.activity.name)
            
            # Exit if the member has opted out of the autoroler
            if member['opt_out']:
                return
            
            # Checks of the activity is an alias first to avoid a potentially unnecessary API call
            if current.activity.name in aliases:
                game_name = aliases[current.activity.name]
                if game_name in games:
                    game = games[game_name]
                else:
                    await admin_channel.send(f"{member.mention} started playing `{current.activity.name}`, and I found an alias with that name, but the game associated with it isn't in the list! Not sure how that happened!")
                    return
            else:     
                # If there isn't a game recorded for the current activity already, add it
                new_games, already_exists, failed_to_find = await AddGames(current.guild, [current.activity.name])
                if len(new_games) > 0:
                    game = list(new_games.values())[0]

                    original_message = f"Hey, guys! Looks like some folks have started playing a new game, <@&{game['role']}>!\n*```yaml\n{game['summary']}```*"
                    view = ListView(original_message, ListType.Select_Game, new_games, current.guild)
                    view.message = await bot_channel.send(original_message + "\nGo ahead and click the button below to add yourself to the role!", view = view, files = await GetImages(new_games))

                elif len(already_exists) > 0:
                    game = list(already_exists.values())[0]
                else:
                    await AddAlias(self.bot, current.guild, current.activity.name, current)
                    return
                
            # Get the role associated with the current activity name (game name)
            role = current.guild.get_role(game['role'])
            
            # Exit if the member doesn't want to be bothered about this game
            if role.name in member['games'] and not member['games'][role.name]['tracked']:
                return
            
            # When somebody starts playing a game and if they are part of the role
            if role in current.roles and role.name in member['games']: 
                await admin_channel.send(f"`{member_display_name}` started playing `{game['name']}`!")
            else:
                # Informs the test channel that the member is playing a game without it's role assigned
                await admin_channel.send(f"`{member_display_name}` started playing `{game['name']}` and/or does not have the role or is not being tracked!")

                # Get the direct message channel from the member
                dm_channel = await current.create_dm()

                # Setup original message
                original_message = f"Hey, `{member_display_name}`! I'm from the [Pavilion Horde Server]({general_channel_link}) and I noticed you were playing `{game['name']}` but don't have the role assigned!"
                
                # Populate view and send direct message
                view = DirectMessageView(original_message, role, current)
                view.message = await dm_channel.send(f"{original_message} Would you like me to add you to it so you'll be notified when someone is looking for a friend?", view = view)
    
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
    async def list_games(self, ctx):
        """Lists the collected game roles for the server."""
        # Get member that sent the command
        member = ctx.message.author

        # List the games if there are more than zero. Otherwise reply with a passive agressive comment
        if len(games) > 0:
            # Convert a long list of games into sets of 25 or less
            message_sets = GetListSets(games, 25)

            # Loop through sets and send a message per
            set_count = 0
            while set_count < len(message_sets):
                if set_count == 0:
                    original_message = f"Here's your game list, {member.mention}!"
                    view = ListView(original_message, ListType.Select_Game, message_sets[set_count], ctx.guild, member)
                    view.message = await ctx.reply(f"{original_message}\n*Please select the games that you're interested in playing:*", view = view)
                else:
                    view = ListView("", ListType.Select_Game, message_sets[set_count], ctx.guild, member)
                    view.message = await ctx.reply(f"", view = view)
                set_count += 1
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
            view = ListView(original_message, ListType.Select_Game, already_exists, ctx.guild, member)
            view.message = await ctx.reply(original_message, view = view)

        elif len(new_games) == 0 and len(already_exists) > 0 and len(failed_to_find) > 0:
            original_message = f"Thanks for the contribution, {member.mention}! I already have {GetNames(already_exists)}, but I don't recognize {GetNames(failed_to_find)}."
            view = ListView(original_message, ListType.Select_Game, already_exists, ctx.guild, member)
            view.message = await ctx.reply(original_message, view = view)

        elif len(new_games) > 0 and len(already_exists) == 0 and len(failed_to_find) == 0:
            original_message = f"Thanks for the contribution, {member.mention}! I've added {GetNames(new_games)} to the list of games!\n*Please select any of the games you're interested in playing below*"
            view = ListView(original_message, ListType.Select_Game, new_games, ctx.guild, member)
            view.message = await ctx.reply(original_message, view = view, files = await GetImages(new_games))
            
        elif len(new_games) > 0 and len(already_exists) == 0 and len(failed_to_find) > 0:
            original_message = f"Thanks for the contribution, {member.mention}! I've added {GetNames(new_games)} to the list of games! But I don't recognize {GetNames(failed_to_find)}.\n*Please select any of the games you're interested in playing below*"
            view = ListView(original_message, ListType.Select_Game, new_games, ctx.guild, member)
            view.message = await ctx.reply(original_message, view = view, files = await GetImages(new_games))
            
        elif len(new_games) > 0 and len(already_exists) > 0 and len(failed_to_find) == 0:
            original_message = f"Thanks for the contribution, {member.mention}! I've added {GetNames(new_games)} to the list of games! I already have {GetNames(already_exists)}.\n*Please select any of the games you're interested in playing below*"
            view = ListView(original_message, ListType.Select_Game, new_games | already_exists, ctx.guild, member)
            view.message = await ctx.reply(original_message, view = view, files = await GetImages(new_games))
            
        elif len(new_games) > 0 and len(already_exists) > 0 and len(failed_to_find) > 0:
            original_message = f"Thanks for the contribution, {member.mention}! I've added {GetNames(new_games)} to the list of games! I already have {GetNames(already_exists)}, but I don't recognize {GetNames(failed_to_find)}.\n*Please select any of the games you're interested in playing below*"
            view = ListView(original_message, ListType.Select_Game, new_games | already_exists, ctx.guild, member)
            view.message = await ctx.reply(original_message, view = view, files = await GetImages(new_games))

    @commands.command()
    async def remove_games(self, ctx):
        """Lists the collected games to select for removal."""
        # Get member that sent the command
        member = ctx.message.author

        # Exits if the member is a bot or isn't whitelisted
        if member.name not in ["sad.panda.", "agvv20", "ashlore.", "malicant999", "goldifish"]:
            return
        
        # Lists the games to remove if there's more than zero. Otherwise reply with a passive agressive comment
        if len(games) > 0:
            list_sets = GetListSets(games, 25)

            set_count = 0
            while set_count < len(list_sets):
                if set_count == 0:
                    original_message = f"Here you go, {member.mention}. Please select the game(s) you'd like to remove..."
                    view = ListView(original_message, ListType.Remove_Game, list_sets[set_count], ctx.guild, member)
                    view.message = await ctx.reply(original_message, view = view) 
                else:
                    view = ListView("", ListType.Remove_Game, list_sets[set_count], ctx.guild, member)
                    view.message = await ctx.reply(view = view)
                set_count += 1
        else:
            await ctx.reply("This is where I would list my games... IF I HAD ANY!")

    @commands.command()
    async def list_aliases(self, ctx):
        """Lists the collected game aliases for the server."""
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
        """Adds an alias to the collection of game aliases for the server."""
        # Get member that sent the command
        member = ctx.message.author

        # Exits if the member is a bot or isn't whitelisted
        if member.name not in ["sad.panda.", "agvv20", "ashlore.", "malicant999", "goldifish"]:
            return
        
        await AddAlias(self.bot, ctx.guild, arg)

    @commands.command()
    async def remove_aliases(self, ctx):
        """Lists the collected game aliases to select for removal."""
        # Get member that sent the command
        member = ctx.message.author

        # Exits if the member is a bot or isn't whitelisted
        if member.name not in ["sad.panda.", "agvv20", "ashlore.", "malicant999", "goldifish"]:
            return
        
        if len(aliases) > 0:
            list_sets = GetListSets(aliases, 25)

            set_count = 0
            while set_count < len(list_sets):
                if set_count == 0:
                    original_message = f"Here you go, {member.mention}. Please select the aliases you'd like to remove..."
                    view = ListView(original_message, ListType.Remove_Alias, list_sets[set_count], ctx.guild, member)
                    view.message = await ctx.reply(original_message, view = view) 
                else:
                    view = ListView("", ListType.Remove_Alias, list_sets[set_count], ctx.guild, member)
                    view.message = await ctx.reply(view = view)
                set_count += 1
        else:
            await ctx.reply("This is where I would list my aliases... IF I HAD ANY!")

    @commands.command()
    async def top_games(self, ctx):
        original_message = f"Hey, {ctx.message.author.mention}! Would you like to see the top games for the server or just yourself?"
        view = PlaytimeView(original_message, ctx.message.author)
        view.message = await ctx.reply(f"{original_message}", view = view)