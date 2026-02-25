import os
from datetime import datetime, timezone

import aiohttp
import discord
from discord.ext import commands

from app.discord_bot.utils import get_matching_type, valid_types, create_basic_embed, create_processing_embed, create_error_embed
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


def _api_headers():
    return {"Authorization": f"Bearer {os.getenv('API_KEY', '')}"}


@commands.command(name="stats")
async def stats(ctx):
    api_url = f"{ctx.bot.base_url}/api/discord-stats"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, headers=_api_headers()) as response:
            if response.status != 200:
                return await ctx.send(embed=create_basic_embed(f"Failed to fetch stats - HTTP code {response.status}"))
            data = await response.json()
            data = data.get("data", data)
            total_profit = float(data.get("total_profit", 0))
            total_cases = data.get("total_cases", "N/A")
            total_spend = float(data.get("total_spend", 0))
            total_return = float(data.get("total_return", 0))
            avg_profit = float(data.get("avg_profit", 0))
            best_type = data.get("most_profitable_case_type") or "N/A"
            top_category = data.get("most_popular_category") or "N/A"
            top_contributor = data.get("top_contributor") or "N/A"
            priciest_item = data.get("most_valuable_item") or "N/A"

    embed = discord.Embed(
        title="Scav Case Tracker Stats",
        color=discord.Color.red(),
    )

    embed.add_field(name="📈 Profit",   value=f"₽{round(total_profit):,}", inline=True)
    embed.add_field(name="💰 Return",   value=f"₽{round(total_return):,}", inline=True)
    embed.add_field(name="💸 Spend",    value=f"₽{round(total_spend):,}", inline=True)

    embed.add_field(name="📦 Cases",    value=f"{total_cases}", inline=True)
    embed.add_field(name="📊 Avg Profit/Case", value=f"₽{round(avg_profit):,}", inline=True)
    embed.add_field(name="🏆 Best Type", value=best_type, inline=True)

    embed.add_field(name="👑 Top Contributor",   value=top_contributor, inline=True)
    embed.add_field(name="💎 Most Expensive Find", value=priciest_item, inline=True)
    embed.add_field(name="🎯 Top Category",  value=top_category, inline=True)

    embed.set_footer(text="Scav Case Tracker Bot")
    embed.set_thumbnail(
        url="https://github.com/Throupy/scav-case-tracker/blob/00d1ebe13240f56f200b52b80214ff8fab69233b/app/static/icon.png?raw=true"
    )
    await ctx.send(embed=embed)


async def _case_embed(session, url, title, color):
    """Fetch a case from url and return a built embed, or an error embed."""
    async with session.get(url, headers=_api_headers()) as response:
        data = await response.json()
        if response.status == 404:
            return create_basic_embed("No cases found.")
        if response.status != 200:
            return create_basic_embed(f"Error fetching case (HTTP {response.status}).")
        data = data["data"]

    items = data.get("items", [])
    total_return = data.get("total_return") or 0
    cost = data.get("cost") or 0
    profit = data.get("profit") or 0
    roi_pct = data.get("roi_pct") or 0
    case_type = data.get("type", "Unknown")
    case_id = data.get("id")
    created_at_raw = data.get("created_at")
    created_at = datetime.fromisoformat(created_at_raw).replace(tzinfo=timezone.utc) if created_at_raw else None
    submitted_by = data.get("submitted_by", "Unknown")
    via_discord = data.get("via_discord", False)

    item_lines = [
        f"• **{item['name']}** x{item['amount']} — ₽{item['total']:,.0f}"
        for item in items
    ]

    submitter_value = f"{submitted_by} via Discord" if via_discord else submitted_by

    embed = discord.Embed(
        title=f"{title} — Case #{case_id} ({case_type})",
        description="\n".join(item_lines) or "No items recorded.",
        color=color,
        timestamp=created_at,
    )
    embed.add_field(name="💰 Return", value=f"₽{total_return:,.0f}", inline=True)
    embed.add_field(name="💸 Cost",   value=f"₽{cost:,.0f}",         inline=True)
    embed.add_field(
        name="📈 Profit" if profit >= 0 else "📉 Profit",
        value=f"₽{profit:,.0f}",
        inline=True,
    )
    embed.add_field(name="📊 ROI",          value=f"{roi_pct:+.1f}%",    inline=True)
    embed.add_field(name="👤 Submitted by", value=submitter_value,        inline=True)
    embed.set_footer(text="Scav Case Tracker")
    return embed


@commands.command(name="best")
async def best_case(ctx):
    async with aiohttp.ClientSession() as session:
        embed = await _case_embed(
            session,
            f"{ctx.bot.base_url}/api/case/best",
            "🏆 Best Case",
            discord.Color.gold(),
        )
    await ctx.send(embed=embed)


@commands.command(name="worst")
async def worst_case(ctx):
    async with aiohttp.ClientSession() as session:
        embed = await _case_embed(
            session,
            f"{ctx.bot.base_url}/api/case/worst",
            "💀 Worst Case",
            discord.Color.dark_red(),
        )
    await ctx.send(embed=embed)


@commands.command(name="case")
async def case_lookup(ctx, case_id: int = None):
    if ctx.bot.guild_id and ctx.guild.id != ctx.bot.guild_id:
        return

    if case_id is None:
        return await ctx.send(embed=create_basic_embed("Usage: `!case <case_id>`"))

    async with aiohttp.ClientSession() as session:
        embed = await _case_embed(
            session,
            f"{ctx.bot.base_url}/api/case/{case_id}",
            f"Case #{case_id}",
            discord.Color.green(),
        )
    await ctx.send(embed=embed)


class ImageDownloaderClient(commands.Bot):
    def __init__(self, download_dir, channel_id, base_url, guild_id=None, manager=None, *args, **kwargs):
        super().__init__(command_prefix="!", *args, **kwargs)
        self.download_dir = download_dir
        self.channel_id = channel_id
        self.base_url = base_url
        self.guild_id = guild_id
        self.manager = manager

        self.add_command(case_types)
        self.add_command(stats)
        self.add_command(case_lookup)
        self.add_command(best_case)
        self.add_command(worst_case)

    async def on_ready(self):
        print(f"Discord Bot Logged in as: {self.user}")
        if self.manager:
            self.manager.bot = self
            await self.manager.flush_pending()

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.channel.id == self.channel_id:
            if message.attachments and message.content:
                scav_case_type = message.content.strip()
                matched_type = get_matching_type(scav_case_type)
                if not matched_type:
                    return await message.channel.send(
                        embed=create_error_embed(
                            "❌ Invalid Case Type",
                            f"**{scav_case_type}** is not a recognised case type.\n"
                            f"Use `!case_types` to see all valid types and their aliases."
                        )
                    )
                for attachment in message.attachments:
                    if attachment.url.split("?")[0].endswith(("jpg", "jpeg", "png")):
                        status_embed = create_processing_embed(
                            "⏳ Processing",
                            f"Received **{matched_type}** submission from {message.author.mention}.\n"
                            f"Downloading image..."
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
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as response:
                    if response.status == 200:
                        file_path = os.path.join(self.download_dir, attachment.filename)
                        with open(file_path, "wb") as f:
                            f.write(await response.read())

                        status_embed.description = (
                            f"Received **{scav_case_type}** submission from {message.author.mention}.\n"
                            f"🔍 Scanning image and fetching prices..."
                        )
                        await status_message.edit(embed=status_embed)

                        await self.submit_image_to_flask(
                            message,
                            file_path,
                            scav_case_type,
                            status_embed,
                            status_message,
                        )
                    else:
                        await status_message.edit(
                            embed=create_error_embed(
                                "❌ Download Failed",
                                f"Could not download the image ({attachment.filename}).\nPlease try again."
                            )
                        )
        except Exception as e:
            await status_message.edit(
                embed=create_error_embed(
                    "❌ Unexpected Error",
                    f"Something went wrong while downloading the image.\n`{str(e)}`"
                )
            )

    async def submit_image_to_flask(
        self, message, image_path, scav_case_type, status_embed, status_message
    ):
        """Submit scav case to Flask using the single unified route"""
        url = f"{self.base_url}/cases/submit"
        headers = {
            "X-BOT-REQUEST": "true",
            "X-BOT-KEY": os.getenv('DISCORD_BOT_API_KEY', 'blank') # fallback to non-None, because None cannot be serialised
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                with open(image_path, "rb") as image_file:
                    form_data = aiohttp.FormData()
                    form_data.add_field("image", image_file,
                                    filename=os.path.basename(image_path))
                    form_data.add_field("scav_case_type", scav_case_type)
                    form_data.add_field("discord_user_id", str(message.author.id))

                    async with session.post(url, headers=headers, data=form_data) as response:
                        response_data = await response.json()

                        if response.status == 200:
                            items = response_data.get("items", [])
                            total_return = response_data.get("total_return") or 0
                            cost = response_data.get("cost") or 0
                            profit = total_return - cost
                            roi_pct = ((profit / cost) * 100) if cost else 0
                            case_id = response_data.get("scav_case_id")

                            item_lines = [
                                f"• **{item['name']}** x{item['quantity']} — ₽{(item['price'] or 0) * item['quantity']:,.0f}"
                                for item in items
                            ]

                            title = f"✅ Scav Case #{case_id} Recorded" if case_id else "✅ Scav Case Recorded"
                            embed = discord.Embed(
                                title=title,
                                description="\n".join(item_lines) or "No items recorded.",
                                color=discord.Color.green(),
                            )
                            embed.add_field(name="💰 Return", value=f"₽{total_return:,.0f}", inline=True)
                            embed.add_field(name="💸 Cost",   value=f"₽{cost:,.0f}",         inline=True)
                            embed.add_field(
                                name="📈 Profit" if profit >= 0 else "📉 Loss",
                                value=f"₽{profit:,.0f}",
                                inline=True,
                            )
                            embed.add_field(name="📊 ROI", value=f"{roi_pct:+.1f}%", inline=True)
                            embed.set_footer(text=f"Submitted by {message.author.display_name} • Scav Case Tracker")
                            await status_message.edit(embed=embed)
                        else:
                            error_msg = response_data.get("error", f"HTTP {response.status}")
                            await status_message.edit(
                                embed=create_error_embed("❌ Submission Failed", error_msg)
                            )

        except Exception as e:
            await status_message.edit(
                embed=create_error_embed(
                    "❌ Connection Error",
                    f"Could not reach the tracker. Please try again later.\n`{str(e)}`"
                )
            )


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
