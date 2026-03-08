#!/bin/bash

# Telegram ACPX Dev Bot Startup Script
# Ensures ZAI_API_KEY is available from environment

cd /root/telegram-acpx-devbot

# Export ZAI_API_KEY from environment if available
if [ -n "$ZAI_API_KEY" ]; then
    export ZAI_API_KEY="$ZAI_API_KEY"
    echo "✅ ZAI_API_KEY loaded from environment (${#ZAI_API_KEY} chars)"
else
    echo "⚠️  ZAI_API_KEY not set in environment"
fi

# Start the bot
/root/telegram-acpx-devbot/venv/bin/python bot.py
