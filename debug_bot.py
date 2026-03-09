#!/usr/bin/env python3
"""
Direct bot runner - bypass PM2 to debug issues
Run this directly to see what's happening
"""
import sys
sys.path.insert(0, '/root/telegram-acpx-devbot')

print("=" * 60)
print("DEBUG: Bot.py Direct Runner")
print("=" * 60)

# Try to import config
try:
    from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS
    print(f"✅ Config imported successfully")
    print(f"   TELEGRAM_BOT_TOKEN: {'SET' if TELEGRAM_BOT_TOKEN else 'NOT SET'}")
    print(f"   ALLOWED_USER_IDS: {ALLOWED_USER_IDS}")
except Exception as e:
    print(f"❌ Config import failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    sys.exit(1)

# Try to import bot modules
try:
    from telegram import Update, Application, CommandHandler, MessageHandler, filters
    from telegram.ext import ContextTypes
    print(f"✅ Telegram imports successful")
except Exception as e:
    print(f"❌ Telegram import failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    sys.exit(1)

# Try to import our modules
try:
    from claude_runner import ClaudeRunner
    from server_tools import get_server_status
    print(f"✅ Custom modules imported successfully")
except Exception as e:
    print(f"❌ Custom modules import failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    sys.exit(1)

# Check bot.py file
print("\nChecking bot.py file...")
try:
    with open('/root/telegram-acpx-devbot/bot.py', 'r') as f:
        content = f.read()
        print(f"✅ bot.py file exists ({len(content)} bytes)")
        
        # Check for imports
        if 'from config import' in content[:1000]:
            print(f"✅ bot.py has 'from config import'")
        else:
            print(f"❌ bot.py MISSING 'from config import'")
            
        # Check for asyncio import
        if 'import asyncio' in content[:500]:
            print(f"✅ bot.py has 'import asyncio'")
        else:
            print(f"❌ bot.py MISSING 'import asyncio'")
            
        # Check for async def main
        if 'async def main():' in content:
            print(f"✅ bot.py has 'async def main():'")
        else:
            print(f"❌ bot.py MISSING 'async def main():'")
            
        # Check for def post_init
        if 'def post_init(application):' in content:
            print(f"✅ bot.py has 'def post_init(application):'")
        else:
            print(f"❌ bot.py MISSING 'def post_init(application):'")
            
except Exception as e:
    print(f"❌ Cannot read bot.py: {e}")

print("\n" + "=" * 60)
print("DEBUG: Complete. Run the bot manually to see real error:")
print("cd /root/telegram-acpx-devbot")
print("source venv/bin/activate")
print("python bot.py")
print("=" * 60)
