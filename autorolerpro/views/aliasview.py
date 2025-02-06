
import discord

class AliasView(discord.ui.View):
    def __init__(self, original_message: str, member: discord.Member = None):
        super().__init__(timeout = 60 * 60 * 24) # Times out after 24 hours 

        