import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    # make this true if you want to 'seed' some data - add X number of entries
    SEED_ENTRIES = False
    SEED_ENTRIES_COUNT = 1
