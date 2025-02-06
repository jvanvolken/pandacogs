
import discord
import traceback

from autorolerpro.utils import LogType

class AliasView(discord.ui.View):
    def __init__(self, original_message: str, alias: str):
        super().__init__(timeout = 60 * 60 * 24) # Times out after 24 hours 
        
        self.original_message = original_message
        self.alias = alias

        self.add_item(self.BlacklistButton(self.original_message, alias))

    # Create a class called YesButton that subclasses discord.ui.Button
    class BlacklistButton(discord.ui.Button):
        def __init__(self, original_message: str, alias: str):
            super().__init__(label = "Blacklist", style = discord.ButtonStyle.success, emoji = "❌")
            self.original_message = original_message
            self.alias = alias

        async def callback(self, interaction):
            try:                
                # TODO: actually blacklist the alias

                # Responds to the request
                await interaction.response.send_message(f"I've blacklisted the `{self.alias}` alias!")
            except Exception as error:
                await interaction.response.send_message(f"I'm sorry, something went wrong! I was unable to blacklist the `{self.alias}` alias!")
                self.Log(f"Unable to blacklist the `{self.alias}` alias!", LogType.ERROR)
                self.Log(traceback.format_exc(), LogType.ERROR)
                self.Log(error, LogType.ERROR)
                raise Exception(error)

    async def on_timeout(self):
        await self.message.edit(content = f"{self.original_message}\n*This request has timed out!*", view = None)
