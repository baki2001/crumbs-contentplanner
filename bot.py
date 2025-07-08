import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install
import discord
import asyncio
from discord.ext import commands
from discord import Intents, app_commands
from config import DISCORD_TOKEN, BOT_PREFIX
from database.database import init_db, AsyncSessionLocal, check_db_health
from sqlalchemy import text
from discord.ext.commands import cooldown, BucketType

# Initialize rich
install()
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, show_time=False, show_path=False)]
)

# Database logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

intents = Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=BOT_PREFIX,
            intents=intents,
            help_command=None
        )
        
    async def setup_hook(self):
        TEST_GUILD_ID = 1014443771393482753
        guild = discord.Object(id=TEST_GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        
        try:
            await self.tree.sync(guild=guild)
            logging.info(f"✅ Commands synced to test guild {TEST_GUILD_ID}")
            await self.tree.sync()
            logging.info("✅ Commands synced globally")
        except Exception as e:
            logging.error(f"❌ Command sync failed: {e}")

bot = MyBot()

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permissions for this command")
    else:
        logging.error(f"Error in {ctx.command}: {error}", exc_info=True)
        await ctx.send(f"❌ An error occurred: {str(error)}")

# Activity tracking
@bot.event
async def on_command_completion(ctx):
    logging.info(f"Command used: {ctx.command} by {ctx.author}")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="for /help"
    ))
    logging.info(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

@bot.hybrid_command(description="Check if the bot is responsive")
@cooldown(1, 5, BucketType.user)
async def ping(ctx):
    await ctx.send("pong 🏓")

@bot.hybrid_command(description="Greet the bot")
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.display_name} 👋")

@bot.hybrid_command(description="Verify database connectivity")
async def dbcheck(ctx):
    try:
        if await check_db_health():
            await ctx.send("✅ Database connection is healthy")
        else:
            await ctx.send("⚠️ Database connection issues detected")
    except Exception as e:
        await ctx.send(f"❌ DB check failed: {e}")

@bot.hybrid_command(description="Show the bot version")
async def version(ctx):
    await ctx.send("🛠 Albion Raid Bot v0.1.1")

@bot.hybrid_command(description="Show server information")
async def serverinfo(ctx):
    if ctx.guild is None:
        return await ctx.send("❌ This command only works in servers")
    embed = discord.Embed(title=f"Server Info: {ctx.guild.name}", color=0x00ff00)
    embed.add_field(name="Members", value=ctx.guild.member_count)
    embed.add_field(name="Created", value=ctx.guild.created_at.strftime("%Y-%m-%d"))
    await ctx.send(embed=embed)

@bot.hybrid_command(description="Show help message")
async def help(ctx):
    embed = discord.Embed(
        title="Albion Raid Planner Help",
        description="**Core Commands**\n"
                   "`/createraid` - Schedule a new raid\n"
                   "`/signup` - Join an existing raid\n\n"
                   "**Utility Commands**",
        color=0x00ff00
    )
    commands_list = [
        ("/ping", "Check if the bot is responsive (5s cooldown)"),
        ("/hello", "Greet the bot"),
        ("/dbcheck", "Verify database connectivity"),
        ("/version", "Show the bot version"),
        ("/serverinfo", "Show server information"),
        ("/help", "Show this help message")
    ]
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)
    await ctx.send(embed=embed)

@bot.hybrid_command(description="Sync commands (owner only)")
@commands.is_owner()
async def sync(ctx: commands.Context):
    """Sync slash commands to the current guild"""
    try:
        if ctx.guild:
            await bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"✅ Commands synced to {ctx.guild.name}")
        else:
            await bot.tree.sync()
            await ctx.send("✅ Commands synced globally")
    except Exception as e:
        await ctx.send(f"❌ Sync failed: {e}")
        logging.error(f"Sync error: {e}")

async def main():
    try:
        await init_db()
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        await bot.close()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass