import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    # make this true if you want to 'seed' some data - add X number of entries
    SEED_ENTRIES = False
    SEED_ENTRIES_COUNT = 1000
    # make this true if you want to add tarkov items (i.e. after new items added to game)
    REFRESH_TARKOV_ITEMS = False
    UPLOAD_FOLDER = "static/uploads/"
    ALLOWED_EXTENSIONS = [".png", ".jpg"]
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16mb
    # discord bot configuration
    START_DISCORD_BOT = False
    DISCORD_CHANNEL_ID = os.getenv("DISCORD_SCAV_CASE_CHANNEL_ID")
    DISCORD_DOWNLOAD_DIR = "app/static/uploads/discord_bot"


# constants
SCAV_CASE_TYPES = ["₽2500", "₽15000", "₽95000", "Moonshine", "Intelligence"]
