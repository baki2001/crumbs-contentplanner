import logging
import asyncio
from discord.ext import commands
from discord import Intents
from config import DISCORD_TOKEN

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.command()
async def ping(ctx):
    await ctx.send("pong.")

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.display_name}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(bot.start(DISCORD_TOKEN))