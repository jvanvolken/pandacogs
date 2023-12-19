# Image and File Manipulation Libraries
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFilter, ImageFont

# Discord Bot Libraries
import discord
from redbot.core import commands


# Cog Directory in AppData
docker_cog_path = "/data/cogs/Welcome"

# Necessary Directories withing the Cog Directory
Avatars_Dir       = docker_cog_path + "/Avatars"
Font_Dir          = docker_cog_path + "/Fonts"

# Define Filepaths
background_image  = docker_cog_path + "/welcome_background.jpg"
avatar_background = docker_cog_path + "/avatar_background.png"
welcome_font      = Font_Dir + "/TheCottage.ttf"

# Fonts:
## TheCottage
## WhiteOnBlack


class WelcomeBanner(commands.Cog):
    """My custom cog"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Demonstrates the welcome message!"""
        await welcome_banner(member, member.guild.system_channel)

    @commands.command()
    async def test_welcome(self, ctx):
        """Demonstrates the welcome message!"""
        await welcome_banner(ctx.message.author, ctx.channel)

    @commands.command()
    async def set_background(self, ctx):
        """Sets the background of the welcome message!"""
        
        # Get important information about the context of the command
        channel = ctx.channel
        author = ctx.message.author

        # Download and save the attachment file
        await ctx.message.attachments[0].save(background_image)

        # Sends message in the command's origin channel
        await channel.send(f"Thanks for the new Welcome Message background, {author.mention}! This will do nicely!")


async def welcome_banner(member, channel):
    # Setup avatar folder and filename
    Path(Avatars_Dir).mkdir(parents=True, exist_ok=True)
    avatar_filename = Avatars_Dir + f"/avatar_{member.id}.png"

    # Download and save the avatar image
    if member.avatar is not None:
        await member.avatar.save(avatar_filename)
    else:
        await member.default_avatar.save(avatar_filename)
    
    # Checks if background image path is a valid file, send just member avatar instead.
    if Path(background_image).is_file():
        # Opens the background and avatar images
        welcome_background = Image.open(background_image)
        avatar_image = Image.open(avatar_filename)

        # Records the width and height of the background and avatar images
        background_width, background_height = welcome_background.size
        avatar_width, avatar_height = avatar_image.size

        #Apply GaussianBlur filter
        blurred_background = welcome_background.filter(ImageFilter.GaussianBlur(5))

        # Set the background's margin
        margins = background_width * 0.06
        
        # Resize avatar image to fit the background
        resize_ratio = (background_height / avatar_height) * 0.4
        resized_avatar = avatar_image.resize((round(avatar_width * resize_ratio), round(avatar_height * resize_ratio)), Image.Resampling.LANCZOS)
        resized_width, resized_height = resized_avatar.size

        # Determines the avatar position early to determine layout
        avatar_position = (round((background_width - resized_width)/2), round(margins * 1.4))

        # Draw shadow and save new background image
        draw = ImageDraw.Draw(blurred_background, "RGBA")
        draw.rounded_rectangle(((margins, margins), (background_width - margins, background_height - margins)), fill=(0, 0, 0, 160), radius = round(background_height * 0.05))

        # Set welcome message and desired width
        clean_name = member.display_name.encode().decode('ascii','ignore') + "!"
        name_size_ratio = 1.2
        welcome_message = f"Welcome to the server,"
        desired_width = (background_width - (margins * 2)) * 0.8
        desired_height = (background_height - margins - avatar_position[1] - resized_height) * 0.8

        # Increase font size until it fills the desired space
        fontsize = 1
        fontwidth = 0
        fontheight = 0
        font = ImageFont.truetype(welcome_font, fontsize)
        while fontwidth < desired_width and fontheight < desired_height:
            fontsize += 1
            fontwidth = (font.getbbox(welcome_message)[2] - font.getbbox(welcome_message)[0])
            fontheight = ((font.getbbox(welcome_message)[3] - font.getbbox(welcome_message)[1])) * 2 * name_size_ratio
            font = ImageFont.truetype(welcome_font, fontsize - 1)

        # Set the member display name fontsize
        name_font = ImageFont.truetype(welcome_font, round(fontsize * name_size_ratio))

        # Get the width and height for each line
        line1_width = font.getbbox(welcome_message)[2] - font.getbbox(welcome_message)[0]
        line1_height = font.getbbox(welcome_message)[3] - font.getbbox(welcome_message)[1]
        line2_width = name_font.getbbox(clean_name)[2] - name_font.getbbox(clean_name)[0]
        line2_height = name_font.getbbox(clean_name)[3] - name_font.getbbox(clean_name)[1]

        # Overlay text onto blurred background
        line1_position = (round((background_width - line1_width)/2), background_height - round(margins * 1.2) - line1_height - line2_height)
        draw.text(line1_position, welcome_message, (209, 202, 192, 255), font = font)
        line2_position = (round((background_width - line2_width)/2), background_height - round(margins * 1.2) - line2_height)
        draw.text(line2_position, clean_name, (209, 202, 192, 255), font = name_font)

        # Draw circle around avatar image
        outline_thickness = 5
        outline_gap = 8
        outlineShape = (
            avatar_position[0] - outline_thickness - outline_gap, 
            avatar_position[1] - outline_thickness - outline_gap,
            avatar_position[0] + resized_avatar.size[0] + outline_thickness + outline_gap, 
            avatar_position[1] + resized_avatar.size[1] + outline_thickness + outline_gap
        )
        draw.ellipse(outlineShape, outline = (209, 202, 192, 255), width = outline_thickness)

        # Construct a circular mask for the avatar image
        mask = Image.new('L', resized_avatar.size, 0)
        draw = ImageDraw.Draw(mask) 
        draw.ellipse((0, 0) + resized_avatar.size, fill=255)
        
        # Overlay avatar onto blurred background
        blurred_background.paste(resized_avatar, avatar_position, mask)

        # Saves the blurred background as the avatar background
        blurred_background.save(avatar_background)

        # Sends a welcome message in the command's origin channel
        await channel.send(f"Welcome to the server, {member.mention}! Make yourself at home!", file = discord.File(avatar_background))
    else:
        await channel.send(f"Hello {member.mention}!", file = discord.File(avatar_filename))