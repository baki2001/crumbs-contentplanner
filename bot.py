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
from config import DISCORD_TOKEN, DATABASE_URL
from database.database import init_db, AsyncSessionLocal
from sqlalchemy import text
from services.template_service import TemplateService
from services.activity_service import ActivityService
from services.user_service import UserService
from rbac import admin_only
from datetime import datetime

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
            command_prefix='!',  # Not used but required
            intents=intents,
            help_command=None
        )
        
    async def setup_hook(self):
        await self.tree.sync()
        logging.info("✅ Slash commands synced globally")

bot = MyBot()

# ======================
# SLASH COMMAND DEFINITIONS
# ======================

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency}ms")

@bot.tree.command(name="dbcheck", description="Verify database connectivity")
async def dbcheck(interaction: discord.Interaction):
    try:
        async with AsyncSessionLocal() as session:
            start = time.perf_counter()
            await session.execute(text("SELECT 1"))
            db_time = round((time.perf_counter() - start) * 1000, 2)
            
            db_host = DATABASE_URL.split('@')[-1].split('/')[0] if '@' in DATABASE_URL else "localhost"
            db_name = DATABASE_URL.split('/')[-1]
            
            await interaction.response.send_message(
                f"✅ Database connection healthy\n"
                f"• Response: {db_time}ms\n"
                f"• Host: `{db_host}`\n"
                f"• Database: `{db_name}`"
            )
    except Exception as e:
        await interaction.response.send_message(f"❌ Connection failed: {str(e)}")

@bot.tree.command(name="addtemplate", description="Create a new activity template")
@app_commands.checks.has_permissions(administrator=True)
async def addtemplate(interaction: discord.Interaction, name: str):
    try:
        if len(name) < 3:
            return await interaction.response.send_message(
                "❌ Template name must be at least 3 characters",
                ephemeral=True
            )
        
        existing = await TemplateService.get_template_by_name(name)
        if existing:
            return await interaction.response.send_message(
                "❌ A template with this name already exists",
                ephemeral=True
            )
        
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
                
                try:
                    slot_definition = json.loads(slot_input)
                except json.JSONDecodeError:
                    try:
                        fixed_input = slot_input.replace("'", '"')
                        slot_definition = json.loads(fixed_input)
                    except:
                        raise ValueError("Invalid JSON format")
                
                for role, data in slot_definition.items():
                    if not isinstance(data, dict):
                        raise ValueError(f"Invalid format for {role}. Should be an object")
                    if 'count' not in data:
                        raise ValueError(f"Missing 'count' for {role}")
                    if 'unlimited' not in data:
                        data['unlimited'] = False
                    if 'emoji' not in data:
                        data['emoji'] = None
                
                template = await TemplateService.create_template(
                    name=name,
                    description=description,
                    slot_definition=slot_definition,
                    creator_id=interaction.user.id,
                    creator_name=interaction.user.display_name
                )
                
                await interaction.response.send_message(
                    f"✅ Created template: **{name}** with {len(slot_definition)} roles"
                )
            except Exception as e:
                logging.error(f"Template creation error: {e}")
                await interaction.response.send_message(
                    f"❌ Failed to create template: {str(e)}",
                    ephemeral=True
                )
        
        modal.on_submit = on_submit
        await interaction.response.send_modal(modal)
        
    except Exception as e:
        logging.error(f"Addtemplate command error: {e}")
        await interaction.response.send_message(
            f"❌ Command failed: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="listtemplates", description="List available templates")
async def listtemplates(interaction: discord.Interaction):
    try:
        templates = await TemplateService.get_all_templates()
        
        if not templates:
            return await interaction.response.send_message("ℹ️ No templates available yet")
        
        embed = discord.Embed(
            title="📋 Activity Templates",
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
                name=f"🔹 {template.name}",
                value=f"{template.description}\n**Slots:** {', '.join(roles)}",
                inline=False
            )
        
        embed.set_footer(text=f"Total templates: {len(templates)}")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logging.error(f"Listtemplates error: {e}")
        await interaction.response.send_message(
            f"❌ Failed to load templates: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="createactivity", description="Schedule a new activity")
async def createactivity(interaction: discord.Interaction, template_name: str):
    try:
        template = await TemplateService.get_template_by_name(template_name)
        if not template:
            return await interaction.response.send_message(
                f"❌ Template '{template_name}' not found",
                ephemeral=True
            )
        
        class ActivityModal(Modal, title=f"Schedule: {template_name}"):
            time_input = TextInput(
                label="Date & Time (YYYY-MM-DD HH:MM UTC)",
                placeholder="2023-12-31 20:00",
                required=True
            )
            location_input = TextInput(
                label="Location",
                placeholder="Brecilien, Caerleon, etc.",
                required=True
            )
            
            async def on_submit(self, interaction: discord.Interaction):
                try:
                    try:
                        scheduled_time = datetime.strptime(self.time_input.value, "%Y-%m-%d %H:%M")
                    except ValueError:
                        await interaction.response.send_message(
                            "❌ Invalid datetime format. Use: YYYY-MM-DD HH:MM",
                            ephemeral=True
                        )
                        return
                    
                    location = self.location_input.value
                    
                    activity = await ActivityService.create_activity(
                        template_id=template.id,
                        scheduled_time=scheduled_time,
                        location=location,
                        creator_id=interaction.user.id,
                        creator_name=interaction.user.display_name
                    )
                    
                    embed = await create_activity_embed(activity)
                    msg = await interaction.channel.send(embed=embed)
                    
                    await ActivityService.update_activity_message(activity.id, interaction.channel.id, msg.id)
                    
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
        
        await interaction.response.send_modal(ActivityModal())
        
    except Exception as e:
        logging.error(f"Createactivity error: {e}")
        await interaction.response.send_message(
            f"❌ Command failed: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="leaveactivity", description="Leave an existing activity")
async def leaveactivity(interaction: discord.Interaction, activity_id: int):
    try:
        participant = await ActivityService.remove_participant(activity_id, interaction.user.id)
        
        if participant:
            activity = await ActivityService.get_activity_by_id(activity_id)
            embed = await create_activity_embed(activity)
            
            channel = bot.get_channel(activity.channel_id)
            if channel:
                try:
                    msg = await channel.fetch_message(activity.message_id)
                    await msg.edit(embed=embed)
                except:
                    logging.warning("Couldn't find activity message")
            
            await interaction.response.send_message(
                "✅ You've left the activity",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ You're not participating in this activity",
                ephemeral=True
            )
    except Exception as e:
        logging.error(f"Leaveactivity error: {e}")
        await interaction.response.send_message(
            f"❌ Failed to leave activity: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="help", description="Show help message")
async def help_command(interaction: discord.Interaction):
    try:
        embed = discord.Embed(
            title="🌟 Albion Activity Planner - Help Menu",
            description="Everything you need to organize Albion Online activities!",
            color=0x3498db
        )
        embed.set_thumbnail(url="https://albiononline.com/static/images/logo/logo.png")
        
        activity_value = (
            "`/createactivity <template>` - Schedule a new activity\n"
            "`/leaveactivity <id>` - Leave an activity by ID\n"
        )
        embed.add_field(name="📅 Activity Scheduling", value=activity_value, inline=False)
        
        template_value = (
            "`/addtemplate <name>` - Create a new activity template\n"
            "`/listtemplates` - List available templates\n"
            "*(Admin only commands)*"
        )
        embed.add_field(name="📋 Template Management", value=template_value, inline=False)
        
        utility_value = (
            "`/ping` - Check bot latency\n"
            "`/dbcheck` - Verify database connectivity\n"
            "`/help` - Show this help message\n"
        )
        embed.add_field(name="⚙️ Utility Commands", value=utility_value, inline=False)
        
        admin_value = "`/sync` - Sync commands (Bot Owner)"
        embed.add_field(name="👑 Admin Commands", value=admin_value, inline=False)
        
        tips = (
            "• All times are in UTC\n"
            "• Use `/listtemplates` to see available activity types\n"
            "• Click role buttons to join activities\n"
            "• Pin activity messages for easy access!"
        )
        embed.add_field(name="💡 Tips", value=tips, inline=False)
        
        embed.set_footer(text="Need more help? Contact your server admin")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logging.error(f"Help command error: {e}")
        await interaction.response.send_message(
            "❌ Failed to display help",
            ephemeral=True
        )

@bot.tree.command(name="sync", description="Sync commands (owner only)")
@app_commands.checks.has_permissions(administrator=True)
async def sync(interaction: discord.Interaction):
    try:
        await interaction.response.defer(thinking=True)
        synced_commands = await bot.tree.sync()
        await interaction.followup.send(f"✅ Synced {len(synced_commands)} commands globally")
    except Exception as e:
        logging.error(f"Sync error: {e}")
        await interaction.followup.send(f"❌ Sync failed: {e}")

# ======================
# SUPPORTING COMPONENTS
# ======================

class RoleSelectionView(discord.ui.View):
    def __init__(self, activity_id, slot_definition):
        super().__init__(timeout=None)
        self.activity_id = activity_id
        self.slot_definition = slot_definition
        
        for role, data in slot_definition.items():
            emoji = data.get('emoji')
            self.add_item(RoleButton(role, emoji, activity_id))

class RoleButton(discord.ui.Button):
    def __init__(self, role, emoji, activity_id):
        if emoji:
            super().__init__(label=role, emoji=emoji, style=discord.ButtonStyle.primary)
        else:
            super().__init__(label=role, style=discord.ButtonStyle.primary)
        self.role = role
        self.activity_id = activity_id
        
    async def callback(self, interaction: discord.Interaction):
        try:
            participant, error = await ActivityService.add_participant(
                self.activity_id,
                interaction.user.id,
                interaction.user.display_name,
                self.role
            )
            
            if participant:
                activity = await ActivityService.get_activity_by_id(self.activity_id)
                embed = await create_activity_embed(activity)
                
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

async def create_activity_embed(activity):
    template = activity.template
    participants = activity.participants
    
    role_participants = {}
    for role in template.slot_definition.keys():
        role_participants[role] = []
    
    for p in participants:
        if p.role in role_participants:
            role_participants[p.role].append(p.user.name)
    
    time_remaining = activity.scheduled_time - datetime.utcnow()
    hours, remainder = divmod(time_remaining.total_seconds(), 3600)
    minutes = remainder // 60
    
    embed = discord.Embed(
        title=f"{template.name} - {activity.location}",
        description=template.description,
        color=0x3498db,
        timestamp=activity.scheduled_time
    )
    
    for role, data in template.slot_definition.items():
        emoji = data.get('emoji', '')
        count = data['count']
        unlimited = data.get('unlimited', False)
        
        current = len(role_participants[role])
        participants_list = "\n".join(role_participants[role]) or "None"
        
        count_display = f"{current}/{count}" if not unlimited else f"{current}+"
        
        embed.add_field(
            name=f"{emoji} {role} ({count_display})",
            value=participants_list,
            inline=True
        )
    
    creator = await UserService.get_user(activity.created_by)
    creator_name = creator.name if creator else "Unknown"
    
    embed.set_footer(text=f"Created by {creator_name}")
    embed.add_field(
        name="⏱️ Time Remaining",
        value=f"{int(hours)}h {int(minutes)}m",
        inline=False
    )
    embed.add_field(
        name="🔢 Activity ID",
        value=f"`{activity.id}`",
        inline=False
    )
    
    return embed

# ======================
# EVENT HANDLERS
# ======================

@bot.event
async def on_ready():
    if not hasattr(bot, 'presence_set'):
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for /help"
        ))
        bot.presence_set = True
        logging.info(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# ======================
# MAIN BOT LOOP
# ======================

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