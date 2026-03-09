#!/bin/bash

# Telegram ACPX Dev Bot Startup Script
# Extracts bot token from OpenClaw config and starts bot

cd /root/telegram-acpx-devbot

# Extract bot token using Python
BOT_TOKEN=$(python3 -c "import json,re; f=open('/root/.openclaw/openclaw.json'); tokens=re.findall(r'\\\"botToken\\\":\\s*\\\"([^\\\"]+)\\\"', f.read()); print(tokens[0] if tokens else '')")

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ ERROR: No bot token found in OpenClaw config"
    exit 1
fi

echo "✅ Bot token extracted (${#BOT_TOKEN} chars)"

# Set environment variables
export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"
export ZAI_API_KEY=$(python3 -c "import json; f=open('/root/.openclaw/openclaw.json'); c=json.load(f); print(c.get('env',{}).get('ZAI_API_KEY',''))")

# Start bot
echo "🚀 Starting Telegram ACPX Dev Bot..."
/root/telegram-acpx-devbot/venv/bin/python bot.py
