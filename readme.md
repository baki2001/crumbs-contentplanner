# Albion Raid Planner Bot

![Albion Online Logo](https://albiononline.com/themes/albion/images/logo.png)

A Discord bot for organizing and managing Albion Online raids with database integration.

## Current Work In Progress
- [ ] Implement `/createraid` command
  - Basic raid creation flow
  - Template selection
  - Date/time picker
- [ ] Design database schema for raid signups
  - Participant roles (Tank/Healer/DPS)
  - Backup slots system
- [ ] Setup automated database backups

## Immediate Backlog (Next Up)
### Core Features
- [ ] `/signup` command with role selection
- [ ] Raid roster display with class icons
- [ ] Automated raid reminders (24h/1h before)
- [ ] Basic permission system (Creator controls)

### Quality of Life
- [ ] Command aliases (!r instead of /raid)
- [ ] Quick-response buttons for common actions
- [ ] Timezone conversion helper

## Technical Debt
- [ ] Refactor database connection handling
- [ ] Improve error logging
- [ ] Add input validation
- [ ] Write unit tests (pytest)

## Future Ideas
### Raid Management
- [ ] Recurring raids system
- [ ] Waitlist/backup system
- [ ] Raid composition validator
- [ ] Gear checklist integration

### Social Features
- [ ] Raid reputation points
- [ ] MVP voting
- [ ] Post-raid feedback system

### Advanced
- [ ] Discord event integration
- [ ] Albion API connection
- [ ] Loot distribution tracker
- [ ] Web dashboard

## Recently Completed
- [x] Hybrid commands system
- [x] Database health checks
- [x] Server info command
- [x] Rich console logging

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/albion-raid-planner.git
   cd albion-raid-planner

---

### File Structure

/albion-raid-planner
├── bot.py                # Main bot logic
├── database
│   ├── __init__.py       # Connection handling
│   ├── models.py         # SQLAlchemy models
│   └── rbac.py           # Permission system
├── config.py             # Environment config
└── requirements.txt      # Dependencies