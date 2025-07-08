import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="secrets.env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_PREFIX = os.getenv("BOT_PREFIX", "/")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]