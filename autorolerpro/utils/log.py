
import os

from datetime import datetime
from enum import Enum

# Log Types
class LogType(Enum):
    INFO    = "INFO"
    DEBUG   = "DEBUG"
    WARNING = "WARNING"
    ERROR   = "ERROR"
    FATAL   = "FATAL"

class LogManager:
    def __init__(self, log_file: str, debug_mode: bool):
        self.log_file = log_file
        self.debug_mode = debug_mode

    # Returns a string formatted datetime of now
    def GetDateTime(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Writes or appends a message to the log_file
    def __call__(self, message: str, log_type: LogType = LogType.INFO):
        if log_type == LogType.DEBUG and not self.debug_mode:
            # Skips debug logs if debug mode is False
            return

        # Formats the log message
        formatted_message = f"{self.GetDateTime()} [{log_type.value}] {message}"

        # Initializes the log file or appends to an existing one
        if os.path.isfile(self.log_file):
            with open(self.log_file, "a") as fp:
                fp.write("\n")
                fp.writelines(formatted_message)
        else:
            with open(self.log_file, "w") as fp:
                fp.writelines(formatted_message)