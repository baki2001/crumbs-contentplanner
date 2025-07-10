import logging
import time
import asyncio
import discord
import json
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install
from discord.ext import commands
from discord import Intents, app_commands
from discord.ui import Modal, TextInput
from config import DISCORD_TOKEN, BOT_PREFIX, DATABASE_URL
from database.database import init_db, AsyncSessionLocal, check_db_health
from sqlalchemy import text
from services.template_service import TemplateService
from database.rbac import admin_only

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
        self.synced = False
        
    async def setup_hook(self):
        if not self.synced:
            try:
                await self.tree.sync()
                self.synced = True
                logging.info("✅ Commands synced globally")
            except Exception as e:
                logging.error(f"Initial command sync error: {e}")

bot = MyBot()

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permissions for this command")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    else:
        logging.error(f"Error in {ctx.command}: {error}", exc_info=True)
        
        try:
            # Try to send error message normally
            await ctx.send(f"❌ An error occurred: {str(error)}")
        except discord.errors.NotFound:
            # Handle "unknown interaction" specifically
            logging.warning("Interaction expired before sending error message")
        except Exception as e:
            logging.error(f"Failed to send error message: {e}")

@bot.event
async def on_ready():
    if not hasattr(bot, 'presence_set'):
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for /help"
        ))
        bot.presence_set = True
        logging.info(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# Core commands
@bot.hybrid_command(description="Check bot latency")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency}ms")

@bot.hybrid_command(description="Verify database connectivity")
async def dbcheck(ctx):
    try:
        async with AsyncSessionLocal() as session:
            start = time.perf_counter()
            await session.execute(text("SELECT 1"))
            db_time = round((time.perf_counter() - start) * 1000, 2)
            
            db_host = DATABASE_URL.split('@')[-1].split('/')[0] if '@' in DATABASE_URL else "localhost"
            db_name = DATABASE_URL.split('/')[-1]
            
            await ctx.send(
                f"✅ Database connection healthy\n"
                f"• Response: {db_time}ms\n"
                f"• Host: `{db_host}`\n"
                f"• Database: `{db_name}`"
            )
    except Exception as e:
        await ctx.send(f"❌ Connection failed: {str(e)}")

# Template management commands
@bot.hybrid_command(description="Create a new activity template")
@admin_only()
async def addtemplate(ctx, name: str):
    """Create a template for activities"""
    try:
        # Validate name
        if len(name) < 3:
            return await ctx.send("❌ Template name must be at least 3 characters", ephemeral=True)
        
        existing = await TemplateService.get_template_by_name(name)
        if existing:
            return await ctx.send("❌ A template with this name already exists", ephemeral=True)
        
        # Create the modal
        modal = Modal(title=f"Create Template: {name}")
        modal.add_item(TextInput(
            label="Description",
            placeholder="Brief description of this activity type",
            required=True,
            min_length=10
        ))
        modal.add_item(TextInput(
            label="Slot Definition (JSON)",
            placeholder='{"Tank": 1, "Healer": 2, "DPS": 5}',
            required=True
        ))
        
        # Handle modal submission
        async def on_submit(interaction: discord.Interaction):
            try:
                description = modal.children[0].value
                slot_input = modal.children[1].value
                
                # Try to parse as JSON
                try:
                    slot_definition = json.loads(slot_input)
                except json.JSONDecodeError:
                    # Try to fix common mistakes: single quotes, missing braces
                    try:
                        # Replace single quotes with double quotes
                        fixed_input = slot_input.replace("'", '"')
                        slot_definition = json.loads(fixed_input)
                    except json.JSONDecodeError:
                        # If still failing, try wrapping in braces
                        try:
                            fixed_input = '{' + slot_input + '}'
                            slot_definition = json.loads(fixed_input)
                        except json.JSONDecodeError:
                            raise ValueError("Invalid JSON format")
                
                if not isinstance(slot_definition, dict):
                    return await interaction.response.send_message(
                        "❌ Slots must be a dictionary (e.g., {'Tank':1, 'Healer':2})",
                        ephemeral=True
                    )
                
                # Validate slot values
                for role, count in slot_definition.items():
                    if not isinstance(count, int) or count < 1:
                        return await interaction.response.send_message(
                            f"❌ Invalid count for {role}: must be positive integer",
                            ephemeral=True
                        )
                
                # Create template
                template = await TemplateService.create_template(
                    name=name,
                    description=description,
                    slot_definition=slot_definition,
                    creator_id=ctx.author.id,
                    creator_name=ctx.author.display_name
                )
                
                await interaction.response.send_message(
                    f"✅ Created template: **{name}** with {sum(slot_definition.values())} slots",
                    ephemeral=False
                )
            except Exception as e:
                logging.error(f"Template creation error: {e}")
                await interaction.response.send_message(
                    f"❌ Failed to create template: {str(e)}",
                    ephemeral=True
                )
        
        modal.on_submit = on_submit
        
        # Send the modal
        await ctx.interaction.response.send_modal(modal)
        
    except Exception as e:
        logging.error(f"Addtemplate command error: {e}")
        await ctx.send(f"❌ Command failed: {str(e)}")

@bot.hybrid_command(description="List available templates")
async def listtemplates(ctx):
    """Show all activity templates"""
    try:
        templates = await TemplateService.get_all_templates()
        
        if not templates:
            return await ctx.send("ℹ️ No templates available yet")
        
        embed = discord.Embed(
            title="Activity Templates",
            description="Available templates for scheduling activities",
            color=0x3498db
        )
        
        for template in templates:
            slots = ", ".join([f"{role}: {count}" for role, count in template.slot_definition.items()])
            embed.add_field(
                name=template.name,
                value=f"{template.description}\n**Slots:** {slots}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    except Exception as e:
        logging.error(f"Listtemplates error: {e}")
        await ctx.send(f"❌ Failed to load templates: {str(e)}")

# Help command
@bot.hybrid_command(description="Show help message")
async def help(ctx):
    try:
        embed = discord.Embed(
            title="Albion Activity Planner Help",
            description="**Template Management**\n"
                      "`/addtemplate <name>` - Create new activity template (Admin)\n"
                      "`/listtemplates` - Show available templates\n\n"
                      "**Utility Commands**",
            color=0x00ff00
        )
        commands_list = [
            ("/ping", "Check bot latency"),
            ("/dbcheck", "Verify database connectivity with details"),
            ("/help", "Show this help message")
        ]
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)
        await ctx.send(embed=embed)
    except Exception as e:
        logging.error(f"Help command error: {e}")
        await ctx.send("❌ Failed to display help")

# Admin commands
@bot.hybrid_command(description="Sync commands (owner only)")
@commands.is_owner()
async def sync(ctx: commands.Context):
    """Sync slash commands"""
    try:
        # Defer the response to prevent timeout
        if ctx.interaction:
            await ctx.interaction.response.defer(thinking=True)
        
        # Perform the sync
        synced_commands = await bot.tree.sync()
        bot.synced = True
        
        # Send confirmation
        await ctx.send(f"✅ Synced {len(synced_commands)} commands globally")
    except Exception as e:
        logging.error(f"Sync error: {e}")
        await ctx.send(f"❌ Sync failed: {e}")

# Main bot loop
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