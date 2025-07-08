import os
import sys
import logging  # Added this import
from dotenv import load_dotenv
from typing import List

load_dotenv(dotenv_path="secrets.env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_PREFIX = os.getenv("BOT_PREFIX", "/")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

def validate_config():
    required = {
        "DISCORD_TOKEN": DISCORD_TOKEN,
        "DATABASE_URL": DATABASE_URL
    }
    
    for name, value in required.items():
        if not value:
            logging.critical(f"Missing required config: {name}")
            sys.exit(1)

validate_config()