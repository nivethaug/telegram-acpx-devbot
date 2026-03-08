"""
Telegram ACPX Dev Bot
A lightweight Telegram bot for running ACPX Claude coding tasks remotely
"""
import os
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import threading

from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS, TELEGRAM_BUFFER_SIZE
from claude_runner import ClaudeRunner
from server_tools import get_server_status


# Global runner instance
runner = ClaudeRunner()
current_task_thread = None


def is_user_allowed(user_id):
    """Check if user is allowed to use the bot"""
    if not ALLOWED_USER_IDS:
        return True  # Allow all if list is empty
    return user_id in ALLOWED_USER_IDS


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    welcome_message = """🤖 **Telegram ACPX Dev Bot**

Welcome! This bot allows you to run ACPX Claude coding tasks remotely.

**Available Commands:**
/dev `<task>` - Run a development task with ACPX Claude
/server - Show server status (CPU, RAM, Disk)
/stop - Stop the currently running task

**Example:**
/dev Create a simple Python web server

Get started by sending a task!"""
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def dev_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dev command"""
    global current_task_thread, runner

    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    # Check if a task is already running
    if runner.is_running:
        await update.message.reply_text("⚠️ A task is already running. Use /stop to cancel it first.")
        return

    # Get task description
    if not context.args:
        await update.message.reply_text("❌ Please provide a task.\n\nUsage: /dev <task description>")
        return

    task = ' '.join(context.args)

    # Send initial message
    status_message = await update.message.reply_text(f"🚀 **Task Started**\n\n```\n{task}\n```", parse_mode='Markdown')

    # Buffer for batched streaming
    output_buffer = []
    BUFFER_SIZE = TELEGRAM_BUFFER_SIZE  # Send updates every N lines (from config)

    # Define callback for batched streaming output
    async def send_output(line):
        nonlocal output_buffer
        output_buffer.append(line)
        
        if len(output_buffer) >= BUFFER_SIZE:
            # Update status message with batched output
            batched_text = "\n".join(output_buffer)
            try:
                await status_message.edit_text(f"🚀 **Task Started**\n\n```\n{task}\n\n{batched_text}```", parse_mode='Markdown')
            except Exception as e:
                print(f"Error editing message: {e}")
            output_buffer.clear()

    # Define async function to flush remaining buffer
    async def flush_buffer():
        nonlocal output_buffer
        if output_buffer:
            batched_text = "\n".join(output_buffer)
            try:
                await status_message.edit_text(f"🚀 **Task Started**\n\n```\n{task}\n\n{batched_text}```", parse_mode='Markdown')
            except Exception as e:
                print(f"Error editing message: {e}")
            output_buffer.clear()

    # Run task in thread
    def run_task():
        return_code = runner.run_task(task, lambda line: context.application.create_task(send_output(line)))

        if return_code == 0:
            context.application.create_task(flush_buffer())
            context.application.create_task(send_output("✅ Task finished successfully"))
        else:
            context.application.create_task(flush_buffer())
            context.application.create_task(send_output(f"⚠️ Task finished with code: {return_code}"))

    current_task_thread = threading.Thread(target=run_task)
    current_task_thread.start()


async def server_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /server command"""
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    status = get_server_status()
    await update.message.reply_text(status, parse_mode='Markdown')


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stop command"""
    global runner

    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    if runner.stop():
        await update.message.reply_text("🛑 Task stopped by user")
    else:
        await update.message.reply_text("ℹ️ No task is currently running")


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown messages"""
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    help_text = """❓ Unknown command.

**Available Commands:**
/dev `<task>` - Run a development task
/server - Show server status
/stop - Stop running task"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


def main():
    """Start the bot"""
    # Check for bot token
    token = os.environ.get('TELEGRAM_BOT_TOKEN') or TELEGRAM_BOT_TOKEN

    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not set!")
        print("Please set it via environment variable:")
        print("  export TELEGRAM_BOT_TOKEN='your-bot-token-here'")
        print("Or edit config.py and add your token.")
        sys.exit(1)

    print("🤖 Starting Telegram ACPX Dev Bot...")

    # Create application
    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("dev", dev_command))
    application.add_handler(CommandHandler("server", server_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_message))

    # Start bot
    print("✅ Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=["message"])


if __name__ == '__main__':
    main()
