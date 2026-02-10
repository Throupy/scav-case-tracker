import os

import aiohttp
import discord
from discord.ext import commands

from app.discord_bot.utils import get_matching_type, valid_types, create_basic_embed
from app.constants import SCAV_CASE_TYPES
from app.models import ScavCase


@commands.command(name="case_types")
async def case_types(ctx):
    embed = discord.Embed(
        title="Scav Case Types",
        description="Here are the valid scav case types and their recognized variations.",
        color=discord.Color.red(),
    )

    # Add each scav case type and its variations as a field
    for valid_type, variations in valid_types.items():
        variations_str = ", ".join(
            variations
        )  # Convert list of variations to a comma-separated string
        embed.add_field(
            name=f"__{valid_type}__ - {variations_str}", value="", inline=False
        )

    embed.set_footer(text="Scav Case Tracker Bot")
    embed.set_thumbnail(
        url="https://github.com/Throupy/scav-case-tracker/blob/00d1ebe13240f56f200b52b80214ff8fab69233b/app/static/icon.png?raw=true"
    )

    await ctx.send(embed=embed)


@commands.command(name="stats")
async def stats(ctx):
    api_url = "http://localhost:5000/api/discord-stats"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            if response.status == 200:
                data = await response.json()
                total_profit = data.get("total_profit", "N/A")
                total_cases = data.get("total_cases", "N/A")
                total_spend = data.get("total_spend", "N/A")
            else:
                total_profit, total_cases, total_spend = "Error", "Error", "Error"

    embed = discord.Embed(
        title="Scav Case Tracker Stats",
        description="Here are the latest statistics:",
        color=discord.Color.red(),
    )

    embed.add_field(
        name="📈 Total Profit", value=f"₽{round(total_profit):,}", inline=False
    )
    embed.add_field(name="📦 Total Cases", value=f"{total_cases}", inline=False)
    embed.add_field(
        name="💸 Total Spend", value=f"₽{round(total_spend):,}", inline=False
    )

    embed.set_footer(text="Scav Case Tracker Bot")
    embed.set_thumbnail(
        url="https://github.com/Throupy/scav-case-tracker/blob/00d1ebe13240f56f200b52b80214ff8fab69233b/app/static/icon.png?raw=true"
    )
    await ctx.send(embed=embed)


class ImageDownloaderClient(commands.Bot):
    def __init__(self, download_dir, channel_id, *args, **kwargs):
        super().__init__(command_prefix="!", *args, **kwargs)
        self.download_dir = download_dir
        self.channel_id = channel_id

        self.add_command(case_types)
        self.add_command(stats)

    async def on_ready(self):
        print(f"Discord Bot Logged in as: {self.user}")

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.channel.id == self.channel_id:
            tarkov_role = discord.utils.get(message.guild.roles, name="EFT")
            if not tarkov_role or tarkov_role not in message.author.roles:
                return await message.channel.send(
                    embed=create_basic_embed(
                        f"You do not have permission to submit scav cases"
                    )
                )

            if message.attachments and message.content:
                scav_case_type = message.content.strip()
                matched_type = get_matching_type(scav_case_type)
                if not matched_type:
                    return await message.channel.send(
                        embed=create_basic_embed(
                            f"{scav_case_type} is not a valid scav case type, use **!case_types** to list valid case types"
                        )
                    )
                for attachment in message.attachments:
                    if attachment.url.split("?")[0].endswith(("jpg", "jpeg", "png")):
                        status_embed = create_basic_embed(
                            f"Received submission for type {matched_type}. Starting processing..."
                        )
                        status_message = await message.channel.send(embed=status_embed)
                        await self.download_image(
                            message,
                            attachment,
                            matched_type,
                            status_embed,
                            status_message,
                        )

        await self.process_commands(message)

    async def download_image(
        self, message, attachment, scav_case_type, status_embed, status_message
    ):
        try:
            # Update the message with current progress
            status_embed.description = (
                "Image downloaded. Performing OCR and retrieving prices..."
            )
            await status_message.edit(embed=status_embed)

            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as response:
                    if response.status == 200:
                        file_path = os.path.join(self.download_dir, attachment.filename)
                        with open(file_path, "wb") as f:
                            f.write(await response.read())

                        status_embed.description = (
                            "Image downloaded. Performing OCR and retrieving prices..."
                        )
                        await status_message.edit(embed=status_embed)

                        # Submit the image to Flask asynchronously
                        await self.submit_image_to_flask(
                            message,
                            file_path,
                            scav_case_type,
                            status_embed,
                            status_message,
                        )
                    else:
                        status_embed.description = (
                            f"Failed to download image: {attachment.filename}"
                        )
                        await status_message.edit(embed=status_embed)
        except Exception as e:
            raise e
            status_embed.description = f"Error downloading image: {str(e)}"
            await status_message.edit(embed=status_embed)

    async def submit_image_to_flask(
        self, message, image_path, scav_case_type, status_embed, status_message
    ):
        """Submit scav case to Flask using the single unified route"""
        url = "http://localhost:5000/submit-scav-case"  # Single route!
        headers = {
            "X-BOT-REQUEST": "true",
            "X-BOT-KEY": os.getenv('DISCORD_BOT_API_KEY')
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                with open(image_path, "rb") as image_file:
                    form_data = aiohttp.FormData()
                    form_data.add_field("image", image_file, 
                                    filename=os.path.basename(image_path))
                    form_data.add_field("scav_case_type", scav_case_type)

                    async with session.post(url, headers=headers, data=form_data) as response:
                        response_data = await response.json()
                        
                        if response.status == 200:
                            await status_message.edit(
                                embed=discord.Embed(
                                    title="✅ Success!",
                                    description=response_data.get("message", "Scav case submitted successfully!"),
                                    color=discord.Color.green()
                                )
                            )
                        else:
                            error_msg = response_data.get("error", f"HTTP {response.status}")
                            await status_message.edit(
                                embed=discord.Embed(
                                    title="❌ Error",
                                    description=f"Failed to submit: {error_msg}",
                                    color=discord.Color.red()
                                )
                            )
                            
        except Exception as e:
            await status_message.edit(
                embed=discord.Embed(
                    title="❌ Connection Error",
                    description=f"Could not connect to Flask app: {str(e)}",
                    color=discord.Color.red()
                )
            )


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
