
from datetime import datetime
from enum import Enum
import os 
import json

# Cog Directory in Appdata
docker_cog_path  = "/data/cogs/GrokBot"
config_file      = f"{docker_cog_path}/config.json"
log_file         = f"{docker_cog_path}/log.txt"

# Log Types
class LogType(Enum):
    Log     = "LOG"
    Debug   = "DEBUG"
    Warning = "WARNING"
    Error   = "ERROR"
    Fatal   = "FATAL"

# Returns a string formatted datetime of now
def GetDateTime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

class FileManager():
    config = None
    
    def __init__(self, default_config: dict):
        # Create directory path if it doesn't already exist
        if not os.path.exists(docker_cog_path):
            os.makedirs(docker_cog_path)

        # Initializes config 
        if os.path.isfile(config_file):
            with open(config_file, "r") as fp:
                self.config = json.load(fp)

            # Add missing default config entries
            for entry, value in default_config.items():
                if entry not in self.config:
                    self.config[entry] = value
        else:
            # Set config to default config and write to file
            self.config = default_config
            with open(config_file, "w") as fp:
                json.dump(self.config, fp, indent = 2, default = str, ensure_ascii = False)

    # Writes or appends a message to the log_file
    def Log(self, message: str, log_type: LogType = LogType.Log):
        # Skips debug logs if debug mode is False
        if log_type == LogType.Debug and not self.config['DebugMode']:
            return
        
        # Initializes the log file or appends to an existing one
        if os.path.isfile(log_file):
            with open(log_file, "a") as fp:
                fp.write("\n")
                fp.writelines(f"{GetDateTime()}: ({log_type.value}) {message}")
        else:
            with open(log_file, "w") as fp:
                fp.writelines(f"{GetDateTime()}: ({log_type.value}) {message}")