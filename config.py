# Configuration for Telegram ACPX Dev Bot
import os


# Project paths
PROJECT_ROOT = "/root/telegram-acpx-devbot"  # Bot source code directory
WORKSPACE_DIR = "/root/workspace/frontend-test"  # AI agent working directory

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8754771378:AAFqdZNwYc8JbZanNy901IQr6lFmJs1gtm4')
ALLOWED_USER_IDS = []

# ACPX configuration
ACPX_CLAUDE_PATH = "/usr/lib/node_modules/openclaw/extensions/acpx/node_modules/acpx/dist/cli.js"

# Bot behavior
MAX_MESSAGE_LENGTH = 4000
TASK_TIMEOUT = 0
TELEGRAM_BUFFER_SIZE = 5
USE_GLM = False

# GLM/ZAI API configuration
ZAI_API_KEY = ""
ZAI_API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
ZAI_MODEL = "glm-4.5"
GLM_DEBUG = True
