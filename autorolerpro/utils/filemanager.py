
from enum import Enum
import json
import os

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
    'ChannelIDs': {
        'General': 000000000000000000,
        'Announcements': 000000000000000000,
        'Admin': 000000000000000000,
        'Test': 000000000000000000
    },
    'Roles': {
        'Admin': 000000000000000000,
        'NewMember': None
    },
    'WhitelistEnabled': False,
    'WhitelistMembers': [],
    'ActivityBlacklist': ["Spotify"],
    'DebugMode': True,
    'AliasMaxAttempts': 5,
    'BackupFrequency': 1,
    'AllowEroticTitles': False,
    'MaxRoleCount': 200,
    'DefaultGameCover': "https://images.igdb.com/igdb/image/upload/t_cover_big/nocover.png"
}

# Flag types
class FlagType(Enum):
    Games    = 1
    Members  = 2
    Aliases  = 3
    Config   = 4

# Dictionary of updated file flags
update_flags = {
    FlagType.Games:   {'status': False, 'comment': ""}, 
    FlagType.Members: {'status': False, 'comment': ""}, 
    FlagType.Aliases: {'status': False, 'comment': ""}, 
    FlagType.Config:  {'status': False, 'comment': ""}
}

# Initializes the privded file and returns true if new
def InitializeFile(file: str) -> any:
    if os.path.isfile(file):
        with open(file, "r") as fp:
            data = json.load(fp)
    else:
        data = {}
        with open(file, "w") as fp:
            json.dump(data, fp, indent = 2, default = str, ensure_ascii = False)

    return data

class FileManager:
    games_file   = None
    members_file = None
    aliases_file = None
    config_file  = None
    log_file     = None

    config  = None
    games   = None
    members = None
    aliases = None

    def __init__(self, docker_cog_path: str):
        self.games_file       = f"{docker_cog_path}/games.json"
        self.members_file     = f"{docker_cog_path}/members.json"
        self.aliases_file     = f"{docker_cog_path}/aliases.json"
        self.config_file      = f"{docker_cog_path}/config.json"
        self.log_file         = f"{docker_cog_path}/log.txt"

        # Create the docker_cog_path if it doesn't already exist
        os.makedirs(docker_cog_path, exist_ok = True)

        # Initializes the config file
        self.config = InitializeFile(self.config_file)

        # Add missing default config entries
        for entry, value in default_config.items():
            if entry not in self.config:
                self.config[entry] = value
                update_flags[FlagType.Config] = {'status': True, 'comment': "Added default configuration item(s)"}

        # Saves the updated config file if necessary
        if update_flags[FlagType.Config]['status']:
            with open(self.config_file, "w") as fp:
                json.dump(self.config, fp, indent = 2, default = str, ensure_ascii = False)

        self.games   = InitializeFile(self.games_file)
        self.members = InitializeFile(self.members_file)
        self.aliases = InitializeFile(self.aliases_file)

    # Updates the specified flag to queue for the backup routine
    def Update(self, flag: FlagType, status: bool = False, comment: str = ""):
        if not status:
            update_flags[flag] = {'status': False, 'comment': ""}
        else:
            update_flags[flag] = {'status': status, 'comment': f"{update_flags[flag]['comment']}\n  --{comment}"}

    # Checks for updates of a particular file and writes to the file
    def CheckForUpdate(self, flag: FlagType, file: str):
        game_flag = update_flags[flag]
        if game_flag['status']:
            with open(file, "w") as fp:
                json.dump(self.games, fp, indent = 2, default = str, ensure_ascii = False) 

            # Adds games file update to log message
            log_message += f"\n  Successfully saved to {file} {game_flag['comment']}"

            # Resets flag
            self.Update(FlagType.Games)

    # Writes or appends a message to the log_file
    def __call__(self):

        print("Hello World")
        