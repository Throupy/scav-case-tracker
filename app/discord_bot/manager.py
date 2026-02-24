import os
import threading
import logging

from sqlalchemy import event
import discord

from app.models import ScavCase
from app.discord_bot.discord_bot import ImageDownloaderClient, intents

class DiscordBotManager:
    """Manages discord bot lifecycle"""

    def __init__(self, app = None) -> None:
        self.app =app
        self.bot = None
        self.bot_thread = None
        self._pending_notifications = []

    def init_app(self, app) -> None:
        """initialise with flask app instance"""
        self.app = app

    def should_start_bot(self) -> bool:
        """detemrine whether the discord bot should be started from the config"""
        if not self.app.config.get("START_DISCORD_BOT"):
            return False

        # only start in main process when debugging
        if self.app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            return False

        return True

    def start_bot(self) -> None:
        """Start the discord bot in a separate thread"""
        if not self.should_start_bot():
            self.app.logger.info("Discord bot startup skipped")
            return

        token = os.getenv("DISCORD_TOKEN")
        if not token:
            self.app.logger.error("DISCORD_TOKEN environment variable not set")
            return
            
        try:
            with self.app.app_context():
                self.bot_thread = threading.Thread(target=self._run_discord_bot)
                self.bot_thread.daemon = True  # Dies when main thread dies
                self.bot_thread.start()
                self.app.logger.info("Discord bot started successfully")
                self._register_db_listeners()
                
        except Exception as e:
            self.app.logger.error(f"Failed to start Discord bot: {e}")

    def _register_db_listeners(self):
        notify_channel_id = self.app.config.get("DISCORD_CHANNEL_ID")
        if not notify_channel_id:
            self.app.logger.warning("DISCORD_CHANNEL_ID not set - DB notifications disabled")
            return

        @event.listens_for(ScavCase, "after_insert")
        def on_new_scav_case(mapper, connection, target):
            embed = discord.Embed(
                title="📦 New Scav Case Submitted",
                color=discord.Color.green(),
            )
            embed.add_field(name="Case ID", value=f"#{target.id}", inline=True)
            embed.add_field(name="Type", value=target.type, inline=True)
            embed.set_footer(text="Scav Case Tracker")

            self.send_notification(
                channel_id=int(notify_channel_id),
                embed=embed,
            )

            self.app.logger.info("Discord DB listeners registered")

    def _run_discord_bot(self):
        try:
            raw_guild_id = self.app.config.get("DISCORD_GUILD_ID")
            discord_bot = ImageDownloaderClient(
                download_dir=self.app.config["DISCORD_DOWNLOAD_DIR"],
                channel_id=int(self.app.config["DISCORD_CHANNEL_ID"]),
                guild_id=int(raw_guild_id) if raw_guild_id else None,
                base_url=self.app.config.get("FLASK_BASE_URL", "http://localhost:5000"),
                intents=intents,
                manager=self,
            )

            discord_bot.run(os.getenv("DISCORD_TOKEN"))
        except Exception as e:
            self.app.logger.error(f"Discord bot error: {e}")

    def send_notification(self, channel_id: int, message: str = None, embed = None) -> None:
        """Send a message to a Discord channel from any thread."""
        if not self.bot or not self.bot.loop or not self.bot.loop.is_running():
            self.app.logger.warning("Discord bot not ready - buffering notification")
            self._pending_notifications.append((channel_id, message, embed))
            return

        asyncio.run_coroutine_threadsafe(
            self._do_send(channel_id, message, embed), self.bot.loop
        )

    async def flush_pending(self):
        """Flush any notifications that were queued before the bot was ready.
        Called from on_ready inside the bot's event loop - no need for threadsafe coro"""
        while self._pending_notifications:
            channel_id, message, embed = self._pending_notifications.pop(0)
            await self._do_send(channel_id, message, embed)

    async def _do_send(self, channel_id: int, message: str = None, embed = None) -> None:
        try:
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(content=message, embed=embed)
            else:
                self.app.logger.error(f"Could not find Discord channel with ID'{channel_id}'")
        except Exception as e:
            self.app.logger.error(f"Failed to send Discord notification: {e}")

# singleton instance  
discord_manager = DiscordBotManager()