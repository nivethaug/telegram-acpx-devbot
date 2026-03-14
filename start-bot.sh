#!/bin/bash

# Telegram ACPX Dev Bot Startup Script
# Uses its own bot token (separate from OpenClaw main bot)

cd /root/telegram-acpx-devbot

# Use the dev bot's own token from config.py
# This is a DIFFERENT bot from the OpenClaw main bot
BOT_TOKEN='8754771378:AAFqdZNwYc8JbZanNy901IQr6lFmJs1gtm4'

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ ERROR: Bot token not set"
    exit 1
fi

echo "✅ Bot token configured (${#BOT_TOKEN} chars)"

# Start bot
echo "🚀 Starting Telegram ACPX Dev Bot..."
/root/telegram-acpx-devbot/venv/bin/python bot.py
