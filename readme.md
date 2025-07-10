
# Albion Online Activity Planner Bot - User Guide

## Getting Started

1. **Invite the bot** to your Discord server with the proper permissions  
2. **Set up admin roles** by configuring `ADMIN_IDS` in secrets.env  
3. **Start the bot** using `python bot.py`

## Command Overview

### Template Management (Admin Only)

#### Create a Template

`/addtemplate <name>`  
text

- Opens a modal to enter:
  - Description
  - Slot definition in JSON format:
    ```json
    {
      "Tank": {"count": 1, "unlimited": false, "emoji": "🛡️"},
      "Healer": {"count": 2, "unlimited": false, "emoji": "❤️"},
      "DPS": {"count": 5, "unlimited": true}
    }
    ```
- Unlimited roles have no participant limits  
- Emojis will appear on role selection buttons

#### List Available Templates

`/listtemplates`  
text

- Shows all created templates with their slot configurations

### Activity Scheduling

#### Create an Activity

`/createactivity <template_name>`  
text

- Opens a modal to enter:
  - Date & Time (UTC format: `YYYY-MM-DD HH:MM`)
  - Location (e.g., "Brecilien", "Caerleon")
- Creates an embed with role selection buttons

#### Join an Activity

- Click the role button on the activity embed  
- Unlimited roles: Always available  
- Limited roles: Only available until slots fill

#### Leave an Activity

`/leaveactivity <activity_id>`  
text

- Activity ID is shown at the bottom of each activity embed

### Utility Commands

#### Check Bot Status

`/ping`  
text

- Returns bot latency

#### Verify Database Connection

`/dbcheck`  
text

- Shows database response time and connection details

## Example Workflow

1. Admin creates a template:

`/addtemplate Avalonian`  
text

```json
{
  "Tank": {"count": 2, "emoji": "🛡️"},
  "Healer": {"count": 4, "emoji": "❤️"},
  "DPS": {"count": 10, "unlimited": true},
  "Scout": {"count": 2, "emoji": "👁️"}
}
```

2. User schedules an activity:  
text  
`/createactivity Avalonian`  
Enters: 2023-12-15 20:00 and Brecilien

3. Participants join:  
Click desired role button on the embed  
Unlimited DPS slots always available  
Limited roles show available slots (e.g., "Tank (1/2)")

4. View scheduled activities:  
Each activity shows:
- Time remaining  
- Participants by role  
- Available slots  
- Location

## Best Practices

**For Admins:**
- Use clear template names (e.g., "Avalonian-10man")
- Set reasonable slot limits
- Include emojis for visual clarity

**For Users:**
- Join activities early for limited roles
- Use `/leaveactivity` if you can't attend
- All times are in UTC

## Troubleshooting

- Commands not appearing? Try `/sync` (owner only)
- Button not working? The bot may have restarted - recreate the activity
- Timezone confusion? All times are displayed in UTC
- Pro Tip: Pin the activity message in your channel for easy access!
