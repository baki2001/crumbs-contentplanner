import logging
import asyncio
from discord.ext import commands
from discord import Intents
from config import DISCORD_TOKEN
from database.database import init_db
from database.database import AsyncSessionLocal
from sqlalchemy import text

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    logging.info(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"❌ Error: {str(error)}")

@bot.command()
async def ping(ctx):
    await ctx.send("pong 🏓")

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.display_name} 👋")

@bot.command()
async def dbcheck(ctx):
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        await ctx.send("✅ Database connection is healthy")
    except Exception as e:
        await ctx.send(f"❌ DB check failed: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    async def main():
        await init_db()
        await bot.start(DISCORD_TOKEN)

    asyncio.run(main())
