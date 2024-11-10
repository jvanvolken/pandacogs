
import os 
import json

# Cog Directory in Appdata
docker_cog_path  = "/data/cogs/GrokBot"
config_file      = f"{docker_cog_path}/config.json"
log_file         = f"{docker_cog_path}/log.txt"

class FileManager():
    config = None
    
    def Initialize(self, default_config: dict):
        # Initializes config 
        if os.path.isfile(config_file):
            with open(config_file, "r") as fp:
                config = json.load(fp)

            # Add missing default config entries
            for entry, value in default_config.items():
                if entry not in config:
                    config[entry] = value
        else:
            config = default_config
            with open(config_file, "w") as fp:
                json.dump(config, fp, indent = 2, default = str, ensure_ascii = False)