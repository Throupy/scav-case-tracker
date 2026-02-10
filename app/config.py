"""
Configuration classes for the scav case tracker flask app.

SEED_ENTRIES: when this is set to true, the application will auto-generate some
              random scav case data for visualisation. The number of scav cases generated
              is controlled by the SEED_ENTRIES_COUNT variable.
REFRESH_TARKOV_ITEMS: when this is set to true, the application will read a new JSON list
                      list of items from ../items.json. I need to include the code for scraping this
                      into the repository, or better yet, add it into the program.
"""

import os
import secrets

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration (shared settings)"""

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///scav_case.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "static/uploads/"
    ALLOWED_EXTENSIONS = [".png", ".jpg"]
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # validated for dev/prod at bottom
    SECRET_KEY = os.getenv("SECRET_KEY")

    DISCORD_CHANNEL_ID = os.getenv("DISCORD_SCAV_CASE_CHANNEL_ID")
    DISCORD_DOWNLOAD_DIR = "app/static/uploads/discord_bot"


class DevelopmentConfig(Config):
    """Config for development"""

    DEBUG = True
    START_DISCORD_BOT = False
    SEED_ENTRIES = False
    SEED_ENTRIES_COUNT = 1000
    REFRESH_TARKOV_ITEMS = False


class ProductionConfig(Config):
    """Config for production"""

    DEBUG = False
    START_DISCORD_BOT = True
    SEED_ENTRIES = False
    SEED_ENTRIES_COUNT = 1000
    REFRESH_TARKOV_ITEMS = False

env = os.getenv(
    "FLASK_ENV", "production"
)  # default to development, set to PRODUCTION in prod

if env == "production":
    ConfigClass = ProductionConfig
    if not Config.SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY must be set in production.\n"
            "Generate one with: \n"
            "\n\tpython -c 'import secrets; print('SECRET_KEY=' + secrets.token_hex(32))' >> .env\n"
        )
else:
    ConfigClass = DevelopmentConfig
    if not Config.SECRET_KEY:
        Config.SECRET_KEY = secrets.token_hex(32)
        print("WARNING: Using auto-generated SECRET_KEY for development.")