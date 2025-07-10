Albion Online Activity Planner Bot - Project Roadmap

Core Concept:
- Discord bot for organizing ALL Albion Online group activities
- Flexible system supporting:
  • Avalonian Dungeons (raids)
  • Ganking Parties
  • PvE Expeditions
  • Gathering Caravans
  • Faction Warfare
  • Hellgates/Crystal League
- Hybrid command system (both prefix and slash commands)
- PostgreSQL database backend

Key Features Implemented:
✓ Hybrid command system
✓ Database integration with health checks
✓ Template management system
  - /addtemplate command
  - /listtemplates command
✓ Role-based access control (admin commands)
✓ Rich console logging
✓ Server information display

Immediate Next Steps (Core Functionality):
1. Activity Scheduling System:
   - /createactivity command
   - Template selection
   - DateTime picker with timezone support
   - Location specification (Brecilien, Caerleon, etc.)

2. Flexible Participation System:
   - /join command with role selection
   - /leave command
   - Role-based slot management
   - Waitlist/backup system

3. Activity Display System:
   - /activityinfo command
   - Embed-based activity cards showing:
     • Time remaining
     • Participants by role
     • Available slots
     • Activity location

4. Notification System:
   - Automated reminders (24h/1h before)
   - Last-minute call notifications

Technical Foundation:
- Python 3.10+
- Discord.py 2.3.2+
- SQLAlchemy 2.0+ (async)
- PostgreSQL 14+
- Rich logging

Database Models:
• ActivityTemplate
  - name, description, slot_definition (JSON)
• Activity
  - template_id, scheduled_time, activity_type, location
• ActivityParticipant
  - role, status (confirmed/backup)

Future Vision:
◆ Web Dashboard (Flask/FastAPI)
  - Admin template management
  - Activity calendar view
  - Participant management
◆ Albion API Integration
  - Character verification
  - Gear score checks
◆ Mobile-friendly interface
◆ Stat tracking and reputation system
◆ Discord event integration

Current Challenges:
- Command synchronization issues
- Template validation refinement
- Timezone handling

Next Session Goals:
1. Implement /createactivity command
2. Create base participation system (/join)
3. Design activity display embed
4. Fix remaining command sync issues

Philosophy:
"Build for flexibility first - all Albion content should be schedulable"
"Focus on mobile-friendly Discord experience"
"Keep admin tools powerful but accessible"