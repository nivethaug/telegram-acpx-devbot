"""
Telegram ACPX Dev Bot
A lightweight Telegram bot for running ACPX Claude coding tasks remotely
"""
import os
import sys
import time
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import threading
from queue import Queue

from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS, TELEGRAM_BUFFER_SIZE, USE_GLM, WORKSPACE_DIR, PROJECT_ROOT, WORKER_COUNT
from claude_runner import ClaudeRunner
from server_tools import get_server_status
import session_manager


# Global runner instance
runner = ClaudeRunner(use_glm=USE_GLM)
current_task_thread = None

# Task queue for concurrent task execution
task_queue = Queue()
workers_running = False


def is_user_allowed(user_id):
    """Check if user is allowed to use bot"""
    if not ALLOWED_USER_IDS:
        return True  # Allow all if list is empty
    return user_id in ALLOWED_USER_IDS


def resolve_project_path(task: str) -> tuple:
    """
    Resolve project path from natural language task.

    Converts prompts like:
    - "build dashboard in crypto-app" -> ("/root/projects/crypto-app", "build dashboard")
    - "fix bug in backend/api-service" -> ("/root/projects/backend/api-service", "fix bug")
    - "create landing page" -> ("/root/projects", "create landing page")

    Returns:
        tuple: (project_path, cleaned_task)
    """
    base = "/root/projects"
    words = task.split()

    # Check for path patterns like "in crypto-app" or "in backend/api-service"
    if " in " in task.lower():
        parts = task.lower().split(" in ", 1)
        if len(parts) == 2:
            project = parts[1].strip().split()[0]  # Get first word after "in"
            project_path = f"{base}/{project}"
            # Remove project reference from task
            cleaned_task = task.replace(f" in {project}", "", 1).replace(f" in {project.upper()}", "", 1).strip()
            return project_path, cleaned_task

    # Check for path patterns like "crypto-app/dashboard"
    for word in words:
        if "/" in word and not word.startswith("/"):
            project_path = f"{base}/{word}"
            # Remove path reference from task
            cleaned_task = task.replace(word, "").strip()
            return project_path, cleaned_task

    # Default: use base projects directory
    return base, task


def improve_task_command(task: str) -> str:
    """
    Convert simple commands to clear AI instructions

    This improves AI response quality by making prompts more explicit.
    Uses tool-style language to ensure ACPX executes commands (not just thinks).
    Also ensures absolute paths for bot source file edits.

    SIMPLIFIED VERSION: Only modify paths, don't restructure natural language prompts.
    """
    task_lower = task.lower().strip()

    # Replace ~ with PROJECT_ROOT for bot file edits
    if '~/' in task or 'telegram-acpx-devbot' in task:
        task = task.replace('~/', f'{PROJECT_ROOT}/')
        # Ensure we use the full absolute path for bot files
        if '/telegram-acpx-devbot/' in task and not task.startswith('/'):
            task = task.replace('/telegram-acpx-devbot/', f'{PROJECT_ROOT}/')

    # Simple file listing - USE TOOL TRIGGER
    if task_lower in ['list files', 'ls', 'ls -la', 'list', 'files']:
        return "Use terminal to run `ls -la` in project directory and list all files and folders."

    # Show structure - USE TOOL TRIGGER
    if task_lower in ['show structure', 'tree', 'structure', 'show project structure']:
        return "Use terminal to run `tree` or `find . -type f -o -type d` to show complete directory structure."

    # Create file - USE TOOL TRIGGER
    if task_lower.startswith('create file'):
        # Extract filename if present
        if 'create file ' in task_lower:
            filename = task[len('create file '):].strip()
            return f"Use the file editor to create a new file named `{filename}` in the project directory."
        return f"{task} - Use the file editor to create it."

    # Edit file - USE TOOL TRIGGER
    if task_lower.startswith('edit file'):
        # Extract filename if present
        if 'edit file ' in task_lower:
            filename = task[len('edit file '):].strip()
            return f"Use the file editor to open `{filename}`, read its current content, then make the requested changes."
        return f"{task} - Use the file editor to modify it."

    # Read file - USE TOOL TRIGGER
    if task_lower.startswith('read'):
        if 'read ' in task_lower:
            filename = task[len('read '):].strip()
            return f"Use the file editor to read and display the complete content of `{filename}`."
        return f"{task} - Use the file editor to display it."

    # Run tests - USE TOOL TRIGGER
    if 'test' in task_lower and len(task_lower) < 20:
        return "Use the terminal to run a test command (npm test, python -m pytest, etc.) and show the results."

    # Build - USE TOOL TRIGGER
    if task_lower in ['build', 'run build']:
        return "Use the terminal to run a build command (npm run build, python setup.py build, etc.) and fix any errors."

    # Default: return original task (with path fixes applied)
    # Don't modify natural language prompts - let ACPX interpret them
    return task


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
/stop - Stop currently running task

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

    # Get task description
    if not context.args:
        await update.message.reply_text("❌ Please provide a task.\n\nUsage: /dev <task description>")
        return

    task = ' '.join(context.args)

    # Check for active session or create temporary one
    user_id = update.effective_user.id
    active_session = session_manager.get_active_session(user_id)

    if active_session:
        # Use existing session's isolated workspace
        workspace_path = os.path.join(active_session["workspace"], "repo")
        project_display = active_session["repo_path"]
        session_id = active_session["session_id"]
        session_type = "existing session"
    else:
        # No active session - resolve project path and create temporary session
        project_path, cleaned_task = resolve_project_path(task)
        temp_session = session_manager.create_session(user_id, project_path)
        if "error" in temp_session:
            await update.message.reply_text(f"❌ {temp_session['message']}")
            return
        workspace_path = os.path.join(temp_session["workspace"], "repo")
        project_display = temp_session["repo_path"]
        session_id = temp_session["session_id"]
        session_type = "temporary session"

    # Mark session as active
    session_manager.set_session_running(session_id, True)

    # Send initial message with project info
    project_name = os.path.basename(project_display)

    # CRITICAL FIX #4: Save initial message object for later updates
    initial_message = await update.message.reply_text(
        f"🚀 Task Started\n\nTask: {task}\n📁 Project: {project_name}\n🔑 Session: {session_id} ({session_type})"
    )

    # Buffer for batched streaming
    output_buffer = []
    BUFFER_SIZE = TELEGRAM_BUFFER_SIZE  # Send updates every N lines (from config)
    MAX_MESSAGE_LENGTH = 3500  # Telegram limit is 4096, keep ~3500 for safety

    # Define callback for streaming output with proper batching
    async def send_output(line):
        nonlocal output_buffer, initial_message

        # Filter out ACPX telemetry noise
        if any(noise in line for noise in ["session/update", "Invalid params", "usageupdate", "size:"]):
            return

        output_buffer.append(line)

        if len(output_buffer) >= BUFFER_SIZE:
            # Get last MAX_MESSAGE_LENGTH chars from buffer (keep recent logs)
            all_text = "\n".join(output_buffer)
            if len(all_text) > MAX_MESSAGE_LENGTH:
                batched_text = "... (truncated)\n" + all_text[-(MAX_MESSAGE_LENGTH - 20):]
            else:
                batched_text = all_text

            try:
                await initial_message.edit_text(
                    f"🚀 Task Started\n📁 Project: {project_name}\n\n{batched_text}"
                )
            except Exception as e:
                print(f"Error editing message: {e}")
            # Don't clear buffer - keep cumulative history

    # Define async function to flush remaining buffer
    async def flush_buffer():
        nonlocal output_buffer, initial_message
        if output_buffer:
            all_text = "\n".join(output_buffer)
            if len(all_text) > MAX_MESSAGE_LENGTH:
                batched_text = "... (truncated)\n" + all_text[-(MAX_MESSAGE_LENGTH - 20):]
            else:
                batched_text = all_text

            try:
                await initial_message.edit_text(
                    f"🚀 Task Started\n📁 Project: {project_name}\n\n{batched_text}"
                )
            except Exception as e:
                print(f"Error flushing buffer: {e}")

    # Get event loop for thread-safe async calls
    loop = asyncio.get_event_loop()

    # Run task in thread with workspace_path
    def run_task():
        # DEBUG: Log task execution start
        print(f"[DEBUG] Starting task: {task}")
        print(f"[DEBUG] Workspace path: {workspace_path}")
        print(f"[DEBUG] Project display: {project_display}")
        print(f"[DEBUG] About to call runner.run_task...")

        # Call runner.run_task with streaming callback
        try:
            return_code = runner.run_task(task, lambda line: asyncio.run_coroutine_threadsafe(send_output(line), loop), project_path=workspace_path)
            print(f"[DEBUG] runner.run_task returned: {return_code}")
            print(f"[DEBUG] Process poll status: {runner.process.poll()}")
            print(f"[DEBUG] Runner is_running: {runner.is_running}")
        except Exception as e:
            print(f"[DEBUG] EXCEPTION in run_task: {e}")
            return_code = -1

        # DEBUG: Log completion
        print(f"[DEBUG] Task thread finished with code: {return_code}")

        # Mark session as not running
        session_manager.set_session_running(session_id, False)

        # ACPX returns -6 (SIGABRT) after successful task when usage reporting fails
        # Treat -6 as success since actual task completed
        # CRITICAL FIX #5: Send completion as REPLY (not edit) to preserve streamed logs
        # This prevents "Processing..." from erasing all useful progress
        if return_code == 0 or return_code == -6:
            # Flush any remaining output first
            asyncio.run_coroutine_threadsafe(flush_buffer(), loop)
            # Send completion as NEW REPLY (not edit) - preserves all logs
            try:
                # Using reply_text() instead of edit_text() creates a new message, not overwrites
                asyncio.run_coroutine_threadsafe(
                    update.message.reply_text(f"\n\n✅ Task finished successfully"),
                    loop
                )
                print(f"[DEBUG] Sent completion message as reply")
            except Exception as e:
                print(f"[DEBUG] Error sending reply: {e}")
        else:
            asyncio.run_coroutine_threadsafe(flush_buffer(), loop)
            asyncio.run_coroutine_threadsafe(send_output(f"⚠️ Task finished with code: {return_code}"), loop)

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


async def workspace_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /workspace command"""
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    workspace_info = f"""📁 **Multi-Project Workspace**

📂 Base Path: `{WORKSPACE_DIR}`

**How to specify projects:**
• `/dev build dashboard in crypto-app` → Creates/uses `/root/projects/crypto-app`
• `/dev fix bug in backend/api` → Creates/uses `/root/projects/backend/api`
• `/dev create landing page` → Uses base `/root/projects`

**Available Commands:**
• `/dev list files` - Show workspace contents
• `/dev show structure` - Show project structure
• `/dev create file <name>` - Create a new file
• `/dev edit file <name>` - Edit an existing file
• `/session` - Manage sessions

*Each task runs in its own project folder.*"""

    await update.message.reply_text(workspace_info, parse_mode='Markdown')


async def session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /session command - Manage sessions"""
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    user_id = update.effective_user.id
    sessions = session_manager.list_sessions(user_id)
    active_session = session_manager.get_active_session(user_id)

    if not sessions:
        await update.message.reply_text(
            "📦 **No active sessions**\n\n"
            "Sessions are created automatically when you run `/dev` commands.\n\n"
            "Use `/session create <path>` to create a persistent session.",
            parse_mode='Markdown'
        )
        return

    # Build session list
    session_list = "📦 **Your Sessions**\n\n"

    for sess in sessions:
        status = "🟢 Active" if sess["running"] else "⏸️ Idle"
        project_name = os.path.basename(sess["repo_path"])
        created_time = int(time.time() - sess["created_at"])
        if created_time < 60:
            time_str = f"{created_time}s ago"
        elif created_time < 3600:
            time_str = f"{created_time // 60}m ago"
        else:
            time_str = f"{created_time // 3600}h ago"

        is_active = " (current)" if sess == active_session else ""

        session_list += (
            f"{status} `{sess['session_id']}`{is_active}\n"
            f"  📁 {project_name}\n"
            f"  ⏱️ {time_str}\n\n"
        )

    session_list += (
        "**Session Commands:**\n"
        "• `/session_create <path>` - Create new session\n"
        "• `/session_close <id>` - Close a session\n"
        "• `/session_cleanup` - Clean old sessions"
    )

    await update.message.reply_text(session_list, parse_mode='Markdown')


async def session_create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /session create command - Create new session"""
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: `/session create <project-path>`\n\n"
            "Example: `/session create /root/projects/my-app`",
            parse_mode='Markdown'
        )
        return

    project_path = context.args[0]
    user_id = update.effective_user.id

    session = session_manager.create_session(user_id, project_path)

    if "error" in session:
        await update.message.reply_text(f"❌ {session['message']}")
    else:
        project_name = os.path.basename(project_path)
        await update.message.reply_text(
            f"✅ Session created!\n\n"
            f"📦 Session ID: `{session['session_id']}`\n"
            f"📁 Project: {project_name}\n"
            f"🔗 Path: `{project_path}`\n\n"
            f"Use `/dev` commands to run tasks in this session.",
            parse_mode='Markdown'
        )


async def session_close_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /session close command - Close a session"""
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: `/session close <session-id>`\n\n"
            "Example: `/session close sess_abc123`",
            parse_mode='Markdown'
        )
        return

    session_id = context.args[0]
    user_id = update.effective_user.id

    session = session_manager.get_session(session_id)

    if not session:
        await update.message.reply_text(f"❌ Session not found: `{session_id}`", parse_mode='Markdown')
        return

    if session["user_id"] != user_id:
        await update.message.reply_text("❌ You don't own this session.")
        return

    if session_manager.close_session(session_id):
        await update.message.reply_text(f"✅ Session closed: `{session_id}`", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ Failed to close session: `{session_id}`", parse_mode='Markdown')


async def session_cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /session cleanup command - Clean old sessions"""
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    cleaned = session_manager.cleanup_sessions(max_age_hours=24)

    if cleaned == 0:
        await update.message.reply_text("✅ No old sessions to clean up.")
    else:
        await update.message.reply_text(f"✅ Cleaned up {cleaned} old session(s).")


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown messages"""
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    help_text = """❓ Unknown command.

**Available Commands:**
/dev `<task>` - Run a development task
/server - Show server status
/workspace - Show current workspace
/stop - Stop running task"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


def main():
    """Starts bot"""
    # Check for bot token
    token = os.environ.get('TELEGRAM_BOT_TOKEN') or TELEGRAM_BOT_TOKEN

    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not set!")
        print("Please set it via environment variable:")
        print("  export TELEGRAM_BOT_TOKEN='your-bot-token-here'")
        print("Or edit config.py and add your token.")
        sys.exit(1)

    # Debug: Print token prefix to verify correct token is being used
    print(f"🔑 Using token starting with: {token[:10]}...")
    if token.startswith('8166539305'):
        print("⚠️ WARNING: Using OpenClaw main bot token! This will cause conflict!")
    elif token.startswith('8754771378'):
        print("✅ Using correct DEV bot token")

    print("🤖 Starting Telegram ACPX Dev Bot...")
    print(f"📁 Multi-project workspace: {WORKSPACE_DIR}")
    print(f"👥 Worker pool size: {WORKER_COUNT}")

    # Create application
    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("dev", dev_command))
    application.add_handler(CommandHandler("server", server_command))
    application.add_handler(CommandHandler("workspace", workspace_command))
    application.add_handler(CommandHandler("session", session_command))
    application.add_handler(CommandHandler("session_create", session_create_command))
    application.add_handler(CommandHandler("session_close", session_close_command))
    application.add_handler(CommandHandler("session_cleanup", session_cleanup_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_message))

    # Start bot
    print("✅ Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=["message"])


if __name__ == '__main__':
    main()
