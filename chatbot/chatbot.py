
import discord
from redbot.core import commands, bot, app_commands


class ChatBot(commands.Cog):
    """ChatBot"""
    def __init__(self, bot: bot.Red):
        self.bot = bot


    @app_commands.command()
    @app_commands.describe(color="Say hello!")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello World!", ephemeral=True)
        

    @app_commands.command()
    @app_commands.describe(color="The color you want to choose")
    @app_commands.choices(color=[
         app_commands.Choice(name="Red", value="red"),
         app_commands.Choice(name="Blue", value="blue"),
    ])
    async def color(self, interaction: discord.Interaction, color: app_commands.Choice[str]):
        await interaction.response.send_message(f"Your color is {color.value}", ephemeral=True)


    zoo = app_commands.Group(name="zoo", description="Zoo related commands")

    @zoo.command(name="add", description="Add an animal to the zoo")
    @app_commands.describe(animal="The animal you want to add")
    async def zoo_add(self, interaction: discord.Interaction, animal: str):
        await interaction.response.send_message(f"Added {animal} to the zoo", ephemeral=True)

    @zoo.command(name="remove", description="Remove an animal from the zoo")
    @app_commands.describe(animal="The animal you want to remove")
    async def zoo_remove(self, interaction: discord.Interaction, animal: str):
        await interaction.response.send_message(f"Removed {animal} from the zoo", ephemeral=True)