"""
Configuration for Telegram ACPX Dev Bot
"""

# Telegram Bot Token (set via environment variable)
TELEGRAM_BOT_TOKEN = "8754771378:AAFqdZNwYc8JbZanNy901IQr6lFmJs1gtm4"

# Allowed user IDs (empty means all users are allowed)
# Add your Telegram user ID to restrict access
ALLOWED_USER_IDS = []

# ACPX Claude Command Path
ACPX_CLAUDE_PATH = "/usr/lib/node_modules/openclaw/extensions/acpx/node_modules/acpx/dist/cli.js"

# Workspace directory for running tasks
WORKSPACE_DIR = "/root/workspace/frontend-test"

# Maximum message length for Telegram (Telegram limit is 4096)
MAX_MESSAGE_LENGTH = 4000

# Task timeout in seconds (0 = no timeout)
TASK_TIMEOUT = 0

# Telegram output buffer size (number of lines before batching)
TELEGRAM_BUFFER_SIZE = 5

# GLM API usage for output summarization
USE_GLM = True  # Enable GLM summarization (ZAI API) - Note: Requires API balance
ZAI_API_KEY = ""  # Set ZAI_API_KEY environment variable or add here
ZAI_API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"  # ZAI API endpoint
ZAI_MODEL = "glm-4.5"  # Model for summarization (ZAI API)
