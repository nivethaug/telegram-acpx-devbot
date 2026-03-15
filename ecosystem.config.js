module.exports = {
  apps: [{
    name: "telegram-acpx-devbot",
    script: "/root/telegram-acpx-devbot/venv/bin/python",
    args: "/root/telegram-acpx-devbot/bot.py",
    cwd: "/root/telegram-acpx-devbot",
    error_file: "/root/.pm2/logs/telegram-acpx-devbot-error.log",
    out_file: "/root/.pm2/logs/telegram-acpx-devbot-out.log",
    pid_file: "/root/.pm2/pids/telegram-acpx-devbot-0.pid"
  }]
}
