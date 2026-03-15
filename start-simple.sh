#!/bin/bash

# Telegram ACPX Dev Bot Startup Script
# Uses its own bot token (separate from OpenClaw main bot)

# Use the dev bot's own token
BOT_TOKEN='8754771378:AAFqdZNwYc8JbZanNy901IQr6lFmJs1gtm4'

if [ -z "$BOT_TOKEN" ]; then
    echo "ERROR: Bot token not set"
    exit 1
fi

echo "Bot token is configured"

# Start bot with absolute paths (no dependency on cd)
echo "Starting Telegram ACPX Dev Bot..."
/root/telegram-acpx-devbot/venv/bin/python /root/telegram-acpx-devbot/bot.py

# Ensure bot process is fully terminated
wait