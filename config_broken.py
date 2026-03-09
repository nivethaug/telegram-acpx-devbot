Configuration for Telegram ACPX Dev Bot

# Telegram Bot Token (set via environment variable)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Allowed user IDs (empty means all users are allowed)
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

# GLM/ZAI API usage for output summarization
USE_GLM = False
ZAI_API_KEY = ""
ZAI_API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
ZAI_MODEL = "glm-4.5"
