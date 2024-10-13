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
    UPLOAD_FOLDER = "static/uploads/"
    ALLOWED_EXTENSIONS = [".png", ".jpg"]
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16mb


# constants
SCAV_CASE_TYPES = ["₽2500", "₽15000", "₽95000", "Moonshine", "Intelligence"]
