class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    START_DISCORD_BOT = False
    SECRET_KEY = "test_secret_key"
    WTF_CSRF_ENABLED = False
    SEED_ENTRIES = False
    SEED_ENTRIES_COUNT = 0
