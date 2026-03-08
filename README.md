# Telegram ACPX Dev Bot

A lightweight Telegram bot for running ACPX Claude coding tasks remotely on your VPS.

## Features

- Run ACPX Claude tasks via Telegram
- Stream task output in real-time
- Monitor server status (CPU, RAM, Disk)
- Stop running tasks
- Fast and reliable execution

## Project Structure

```
telegram-acpx-devbot/
├── bot.py              # Main Telegram bot application
├── claude_runner.py    # ACPX Claude task runner
├── server_tools.py     # Server monitoring utilities
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Installation

1. **Create virtual environment and install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set up Telegram Bot Token:**

   Create a bot via [@BotFather](https://t.me/botfather) on Telegram and get your token.

   Set it as an environment variable:
   ```bash
   export TELEGRAM_BOT_TOKEN='your-bot-token-here'
   ```

   Or add it directly to `config.py`.

3. **Activate virtual environment and run the bot:**
   ```bash
   source venv/bin/activate
   python bot.py
   ```

## Commands

- `/start` - Show welcome message and available commands
- `/dev <task>` - Run a development task with ACPX Claude
- `/server` - Display server status (CPU, RAM, Disk usage)
- `/stop` - Stop the currently running task

## Usage Examples

```
/dev Create a simple Python web server
/dev Write a function to calculate fibonacci numbers
/dev Debug this code: [paste code]
```

## Configuration

Edit `config.py` to customize:

- `TELEGRAM_BOT_TOKEN` - Your bot token
- `ALLOWED_USER_IDS` - Restrict access to specific Telegram users
- `WORKSPACE_DIR` - Directory where tasks are executed
- `MAX_MESSAGE_LENGTH` - Maximum message size for Telegram

## Safety Rules

- Only `/dev` commands can execute tasks
- All tasks run through ACPX Claude
- No arbitrary shell execution allowed
- Tasks can be stopped with `/stop`

## System Requirements

- Python 3.7+
- Node.js (for ACPX Claude)
- ACPX CLI installed at `/usr/lib/node_modules/openclaw/extensions/acpx/node_modules/acpx/dist/cli.js`

## Running as a Service

To run the bot permanently in the background:

Using systemd:
```bash
# Create service file
sudo nano /etc/systemd/system/telegram-acpx-bot.service
```

```
[Unit]
Description=Telegram ACPX Dev Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/telegram-acpx-devbot
Environment="TELEGRAM_BOT_TOKEN=your-token-here"
ExecStart=/root/telegram-acpx-devbot/venv/bin/python /root/telegram-acpx-devbot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable telegram-acpx-bot
sudo systemctl start telegram-acpx-bot
```

## Future Phases

- Redis task queue
- Worker processes for parallel execution
- Project-specific workspaces
- Task history and logs

## License

MIT
