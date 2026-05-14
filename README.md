# GlacierBot

A Discord bot for Roblox game applications, suggestions, and events.

---

## Features
- **Applications** — Receives Roblox webhook data and posts styled embeds with ✅/❌ for staff review
- **Suggestions** — Auto-adds ✅/❌/🟡 to any message in the suggestions channel
- **Events** — `/event` command posts styled event embeds with live 🎉 RSVP count

---

## Setup

### 1. Install & run
```bash
pip install -r requirements.txt
export DISCORD_TOKEN="your-token"
python bot.py
```

### 2. Configure in Discord
```
/setup applications_channel:#applications suggestions_channel:#suggestions events_channel:#events staff_role:@Staff
```

### 3. Set webhook secret (optional but recommended)
```
/set_webhook_secret secret:your-secret-key
```

---

## Roblox Integration

The bot runs an HTTP server on port 5000 (or `$PORT` env var).
Send a POST request to `https://your-railway-url/application` with this JSON body:

```json
{
  "type": "staff",
  "username": "PlayerName",
  "userId": 123456789,
  "timestamp": "05/13/2026 10:00 AM UTC",
  "answers": {
    "Why do you want to join?": "Because I love the game.",
    "How old are you?": "16",
    "Do you have experience?": "Yes, 2 years."
  }
}
```

### Roblox Lua example:
```lua
local HttpService = game:GetService("HttpService")

local data = {
    type = "staff",
    username = game.Players.LocalPlayer.Name,
    userId = game.Players.LocalPlayer.UserId,
    answers = {
        ["Why do you want to join?"] = "My answer here",
        ["How old are you?"] = "16",
    }
}

local response = HttpService:RequestAsync({
    Url = "https://your-railway-url/application",
    Method = "POST",
    Headers = {
        ["Content-Type"] = "application/json",
        ["Authorization"] = "Bearer your-secret-key"
    },
    Body = HttpService:JSONEncode(data)
})
```

### Application types (controls embed color):
- `staff` — Blue
- `moderator` — Orange
- `builder` — Green
- `default` — Grey

---

## Slash Commands

| Command | Description | Permission |
|---|---|---|
| `/setup` | Configure channels and roles | Server Admin |
| `/set_webhook_secret` | Set Roblox webhook secret | Admin Role |
| `/event` | Post an event embed with RSVP | Staff Role |
| `/status` | Show current configuration | Admin Role |

---

## Deploying on Railway
1. Push to GitHub
2. New Railway project → Deploy from GitHub
3. Add environment variables: `DISCORD_TOKEN`, optionally `APP_WEBHOOK_SECRET`
4. Railway exposes a public URL — use that as your Roblox webhook URL
