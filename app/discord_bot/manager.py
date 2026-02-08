import os
import threading
import logging

from app.discord_bot.discord_bot import ImageDownloaderClient, intents

class DiscordBotManager:
    """Manages discord bot lifecycle"""

    def __init__(self, app = None) -> None:
        self.app =app
        self.bot_thread = None

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
                
        except Exception as e:
            self.app.logger.error(f"Failed to start Discord bot: {e}")

    def _run_discord_bot(self):
        """Internal method to run the Discord bot"""
        try:
            discord_bot = ImageDownloaderClient(
                download_dir=self.app.config["DISCORD_DOWNLOAD_DIR"],
                channel_id=int(self.app.config["DISCORD_CHANNEL_ID"]),
                intents=intents,
            )
            discord_bot.run(os.getenv("DISCORD_TOKEN"))
            
        except Exception as e:
            self.app.logger.error(f"Discord bot error: {e}")


# singleton instance  
discord_manager = DiscordBotManager()