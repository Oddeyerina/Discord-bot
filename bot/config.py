import os

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["DISCORD_GUILD_ID"])
DATABASE_URL = os.environ["DATABASE_URL"]
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
SESSION_SECRET = os.environ["SESSION_SECRET"]
