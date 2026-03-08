module.exports = {
  apps: [{
    name: 'telegram-acpx-devbot',
    script: 'bot.py',
    cwd: '/root/telegram-acpx-devbot',
    interpreter: '/root/telegram-acpx-devbot/venv/bin/python',
    env: {
      ZAI_API_KEY: process.env.ZAI_API_KEY || ''
    },
    max_memory_restart: '500M',
    error_file: '/root/.pm2/logs/telegram-acpx-devbot-error.log',
    out_file: '/root/.pm2/logs/telegram-acpx-devbot-out.log',
    log_file: '/root/.pm2/logs/telegram-acpx-devbot-combined.log',
    time: true,
    merge_logs: true,
    autorestart: true,
    watch: false,
    max_restarts: 10,
    min_uptime: '10s',
    restart_delay: 4000
  }]
};
