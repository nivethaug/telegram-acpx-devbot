"""
Telegram ACPX Dev Bot
A lightweight Telegram bot for running ACPX Claude coding tasks remotely
"""
import os
import sys
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import threading

from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS
from claude_runner import ClaudeRunner
from server_tools import get_server_status


# Global runner instance
runner = ClaudeRunner()
current_task_thread = None

# Status heartbeat variables
status_loop_task = None
current_task_description = None
status_message_id = None
STATUS_INTERVAL = 120  # 2 minutes in seconds


def is_user_allowed(user_id):
    """Check if user is allowed to use the bot"""
    if not ALLOWED_USER_IDS:
        return True  # Allow all if list is empty
    return user_id in ALLOWED_USER_IDS


async def status_update_coroutine(update, task_description, stop_event):
    """
    Send periodic status updates every 2 minutes while task is running
    
    Args:
        update: Telegram update object for sending messages
        task_description: Description of current task
        stop_event: asyncio.Event to signal when to stop
    """
    global status_message_id
    
    # Send initial status message
    status_text = f"⏳ Agent still working...\n\nTask: {task_description}"
    message = await update.message.reply_text(status_text)
    status_message_id = message.message_id
    
    # Loop until stop event is set
    while not stop_event.is_set():
        try:
            await asyncio.sleep(STATUS_INTERVAL)
            
            # Check if task is still running
            if not runner.is_running:
                break
                
            # Send update to the same message
            try:
                elapsed_text = f"\n\n⏳ Agent still working...\nTask: {task_description}"
                await update.message.reply_text(elapsed_text, reply_to_message_id=status_message_id)
            except Exception as e:
                print(f"Error sending status update: {e}")
                break
                
        except asyncio.CancelledError:
            break


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
    global current_task_thread, runner, status_loop_task, current_task_description, status_message_id

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
    
    # Store task description for status updates
    current_task_description = task
    
    # Create stop event for status loop
    stop_event = asyncio.Event()

    # Send initial message
    await update.message.reply_text(f"🚀 **Task Started**\n\n```\n{task}\n```", parse_mode='Markdown')

    # Define callback for streaming output
    async def send_output(line):
        try:
            await update.message.reply_text(line)
        except Exception as e:
            print(f"Error sending message: {e}")

    # Run task in thread
    def run_task():
        global status_loop_task
        
        # Start status update loop
        stop_event.clear()
        status_loop_task = asyncio.create_task(
            status_update_coroutine(update, task, stop_event)
        )
        
        # Send initial status messages
        for line in [f"🚀 Task started", f"Running: {task}"]:
            context.application.create_task(send_output(line))

        return_code = runner.run_task(task, lambda line: context.application.create_task(send_output(line)))

        if return_code == 0:
            context.application.create_task(send_output("✅ Task finished successfully"))
        else:
            context.application.create_task(send_output(f"⚠️ Task finished with code: {return_code}"))
        
        # Task finished - stop status loop
        stop_event.set()
        if status_loop_task and not status_loop_task.done():
            status_loop_task.cancel()
        
        # Clear task description
        current_task_description = None
        status_message_id = None
        status_loop_task = None

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
    global runner, current_task_description, status_loop_task

    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    if runner.stop():
        await update.message.reply_text("🛑 Task stopped by user")
        
        # Stop status loop if running
        if status_loop_task and not status_loop_task.done():
            status_loop_task.cancel()
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
