
import discord
from redbot.core import commands, bot, app_commands


class ChatBot(commands.Cog):
    """ChatBot"""
    def __init__(self, bot: bot.Red):
        self.bot = bot

