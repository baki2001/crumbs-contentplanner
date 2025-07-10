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
from discord.ui import Modal, TextInput, Button
from config import DISCORD_TOKEN, BOT_PREFIX, DATABASE_URL
from database.database import init_db, AsyncSessionLocal, check_db_health
from sqlalchemy import text
from services.template_service import TemplateService
from services.activity_service import ActivityService
from services.user_service import UserService
from database.rbac import admin_only
from datetime import datetime, timedelta

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
            placeholder='{"Tank": {"count":1, "unlimited":false, "emoji":"🛡️"}, "DPS": {"count":5, "unlimited":true}}',
            required=True
        ))
        
        async def on_submit(interaction: discord.Interaction):
            try:
                description = modal.children[0].value
                slot_input = modal.children[1].value
                
                # Parse slot definitions
                try:
                    slot_definition = json.loads(slot_input)
                except json.JSONDecodeError:
                    # Try to fix common mistakes
                    try:
                        fixed_input = slot_input.replace("'", '"')
                        slot_definition = json.loads(fixed_input)
                    except:
                        raise ValueError("Invalid JSON format")
                
                # Validate structure
                for role, data in slot_definition.items():
                    if not isinstance(data, dict):
                        raise ValueError(f"Invalid format for {role}. Should be an object")
                    if 'count' not in data:
                        raise ValueError(f"Missing 'count' for {role}")
                    if 'unlimited' not in data:
                        data['unlimited'] = False  # Default to limited
                    if 'emoji' not in data:
                        data['emoji'] = None  # Default no emoji
                
                # Create template
                template = await TemplateService.create_template(
                    name=name,
                    description=description,
                    slot_definition=slot_definition,
                    creator_id=ctx.author.id,
                    creator_name=ctx.author.display_name
                )
                
                await interaction.response.send_message(
                    f"✅ Created template: **{name}** with {len(slot_definition)} roles",
                    ephemeral=False
                )
            except Exception as e:
                logging.error(f"Template creation error: {e}")
                await interaction.response.send_message(
                    f"❌ Failed to create template: {str(e)}",
                    ephemeral=True
                )
        
        modal.on_submit = on_submit
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
            roles = []
            for role, data in template.slot_definition.items():
                emoji = data.get('emoji', '')
                count = "∞" if data.get('unlimited', False) else data['count']
                roles.append(f"{emoji} {role}: {count}")
            
            embed.add_field(
                name=template.name,
                value=f"{template.description}\n**Slots:** {', '.join(roles)}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    except Exception as e:
        logging.error(f"Listtemplates error: {e}")
        await ctx.send(f"❌ Failed to load templates: {str(e)}")

# Activity Scheduling Commands
@bot.hybrid_command(description="Schedule a new activity")
async def createactivity(ctx, template_name: str):
    """Create a new activity from a template"""
    try:
        # Get template
        template = await TemplateService.get_template_by_name(template_name)
        if not template:
            return await ctx.send(f"❌ Template '{template_name}' not found", ephemeral=True)
        
        # Create modal for activity details
        modal = Modal(title=f"Schedule: {template_name}")
        modal.add_item(TextInput(
            label="Date & Time (YYYY-MM-DD HH:MM UTC)",
            placeholder="2023-12-31 20:00",
            required=True
        ))
        modal.add_item(TextInput(
            label="Location",
            placeholder="Brecilien, Caerleon, etc.",
            required=True
        ))
        
        async def on_submit(interaction: discord.Interaction):
            try:
                # Parse datetime
                dt_str = modal.children[0].value
                try:
                    scheduled_time = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    return await interaction.response.send_message(
                        "❌ Invalid datetime format. Use: YYYY-MM-DD HH:MM",
                        ephemeral=True
                    )
                
                location = modal.children[1].value
                
                # Create activity
                activity = await ActivityService.create_activity(
                    template_id=template.id,
                    scheduled_time=scheduled_time,
                    location=location,
                    creator_id=ctx.author.id,
                    creator_name=ctx.author.display_name
                )
                
                # Create activity display
                embed = await create_activity_embed(activity)
                msg = await ctx.channel.send(embed=embed)
                
                # Store message reference
                await ActivityService.update_activity_message(activity.id, ctx.channel.id, msg.id)
                
                # Add role selection buttons
                view = RoleSelectionView(activity.id, template.slot_definition)
                await msg.edit(view=view)
                
                await interaction.response.send_message(
                    f"✅ Activity scheduled for {scheduled_time} in {location}",
                    ephemeral=True
                )
            except Exception as e:
                logging.error(f"Activity creation error: {e}")
                await interaction.response.send_message(
                    f"❌ Failed to create activity: {str(e)}",
                    ephemeral=True
                )
        
        modal.on_submit = on_submit
        await ctx.interaction.response.send_modal(modal)
        
    except Exception as e:
        logging.error(f"Createactivity error: {e}")
        await ctx.send(f"❌ Command failed: {str(e)}")

# Role selection buttons
class RoleSelectionView(discord.ui.View):
    def __init__(self, activity_id, slot_definition):
        super().__init__(timeout=None)
        self.activity_id = activity_id
        self.slot_definition = slot_definition
        
        # Create a button for each role
        for role, data in slot_definition.items():
            emoji = data.get('emoji')
            self.add_item(RoleButton(role, emoji, activity_id))

class RoleButton(discord.ui.Button):
    def __init__(self, role, emoji, activity_id):
        # Use emoji if available
        if emoji:
            super().__init__(label=role, emoji=emoji, style=discord.ButtonStyle.primary)
        else:
            super().__init__(label=role, style=discord.ButtonStyle.primary)
        self.role = role
        self.activity_id = activity_id
        
    async def callback(self, interaction: discord.Interaction):
        try:
            # Join activity with selected role
            participant, error = await ActivityService.add_participant(
                self.activity_id,
                interaction.user.id,
                interaction.user.display_name,
                self.role
            )
            
            if participant:
                # Update activity display
                activity = await ActivityService.get_activity_by_id(self.activity_id)
                embed = await create_activity_embed(activity)
                
                # Find the message to update
                channel = bot.get_channel(activity.channel_id)
                if channel:
                    try:
                        msg = await channel.fetch_message(activity.message_id)
                        await msg.edit(embed=embed)
                    except:
                        logging.warning("Couldn't find activity message")
                
                await interaction.response.send_message(
                    f"✅ Joined as {self.role}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ {error}",
                    ephemeral=True
                )
        except Exception as e:
            logging.error(f"Role selection error: {e}")
            await interaction.response.send_message(
                f"❌ Failed to join activity: {str(e)}",
                ephemeral=True
            )

@bot.hybrid_command(description="Leave an activity")
async def leaveactivity(ctx, activity_id: int):
    """Leave an existing activity"""
    try:
        # Remove participant
        participant = await ActivityService.remove_participant(activity_id, ctx.author.id)
        
        if participant:
            # Update activity display
            activity = await ActivityService.get_activity_by_id(activity_id)
            embed = await create_activity_embed(activity)
            
            # Find the message to update
            channel = bot.get_channel(activity.channel_id)
            if channel:
                try:
                    msg = await channel.fetch_message(activity.message_id)
                    await msg.edit(embed=embed)
                except:
                    logging.warning("Couldn't find activity message")
            
            await ctx.send("✅ You've left the activity", ephemeral=True)
        else:
            await ctx.send("❌ You're not participating in this activity", ephemeral=True)
    except Exception as e:
        logging.error(f"Leaveactivity error: {e}")
        await ctx.send(f"❌ Failed to leave activity: {str(e)}")

# Activity Embed Creation
async def create_activity_embed(activity):
    # Get activity details
    template = activity.template
    participants = activity.participants
    
    # Group participants by role
    role_participants = {}
    for role in template.slot_definition.keys():
        role_participants[role] = []
    
    for p in participants:
        if p.role in role_participants:
            role_participants[p.role].append(p.user.name)
    
    # Calculate time remaining
    time_remaining = activity.scheduled_time - datetime.utcnow()
    hours, remainder = divmod(time_remaining.total_seconds(), 3600)
    minutes = remainder // 60
    
    # Create embed
    embed = discord.Embed(
        title=f"{template.name} - {activity.location}",
        description=template.description,
        color=0x3498db,
        timestamp=activity.scheduled_time
    )
    
    # Add fields for each role
    for role, data in template.slot_definition.items():
        emoji = data.get('emoji', '')
        count = data['count']
        unlimited = data.get('unlimited', False)
        
        current = len(role_participants[role])
        participants_list = "\n".join(role_participants[role]) or "None"
        
        # Show unlimited as ∞
        count_display = f"{current}/{count}" if not unlimited else f"{current}+"
        
        embed.add_field(
            name=f"{emoji} {role} ({count_display})",
            value=participants_list,
            inline=True
        )
    
    # Add metadata
    creator = await UserService.get_user(activity.created_by)
    creator_name = creator.name if creator else "Unknown"
    
    embed.set_footer(text=f"Created by {creator_name}")
    embed.add_field(
        name="Time Remaining",
        value=f"{int(hours)}h {int(minutes)}m",
        inline=False
    )
    embed.add_field(
        name="Activity ID",
        value=f"`{activity.id}`",
        inline=False
    )
    
    return embed

# Help command
@bot.hybrid_command(description="Show help message")
async def help(ctx):
    try:
        embed = discord.Embed(
            title="Albion Activity Planner Help",
            description="**Activity Scheduling**\n"
                      "`/createactivity <template>` - Schedule a new activity\n"
                      "`/leaveactivity <id>` - Leave an activity\n\n"
                      "**Template Management**\n"
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