# 🥅 GoalKeeper CLI

GoalKeeper is a persistent, zero-overhead notification layer for AI coding agents. It sends real-time Telegram notifications (and supports future notification backends) for permission prompts, rate limits, task completions, and rolling quota resets across developer command-line interfaces: **Claude Code (`claude`)**, **OpenAI Codex (`codex`)**, and **Google's Antigravity CLI (`agy`)**.

---

## 🏛️ Extensible Architecture

GoalKeeper is designed with a premium, extensible architecture:
1. **Agent Adapters**: All agents conform to the `AgentAdapter` interface, which maps native events to a common event model.
2. **Common Event Model**: Defines unified event objects (`GoalKeeperEvent`) including `session_start`, `permission_required`, `rate_limit_hit`, `quota_refresh`, `task_completed`, and `task_failed`.
3. **Pluggable Notification Providers**: Integrates notifications via `NotificationProvider` backends (e.g. `TelegramProvider`, with future support for Slack, Discord, Pushover, etc.).
4. **Event Dispatcher**: A single centralized dispatch pipeline (`dispatch_event`) to format notifications, schedule quota reset reminders, and log audits.

---

## 🔒 Security & Privacy Architecture

GoalKeeper is designed with a premium, secure user experience that **does not expose the Telegram Bot Token** and requires **zero custom bot configuration** by default.

### How it works:
1. **The Shared Bot (`@GoalKeeperCliBot`)**: Instead of requiring every user to create a bot via `@BotFather`, users simply start a chat with `@GoalKeeperCliBot`. The bot instantly replies with their private, unique Telegram `chat_id` (e.g., `123456789`).
2. **The Secure Message Proxy**: When sending a notification, goalkeeper sends a POST request containing only the message text and your `chat_id` to your secure proxy API (`https://api.goalkeeper.dev/notify`). The proxy server appends the secret `TELEGRAM_BOT_TOKEN` (hidden safely in the backend environment variables) and forwards the message to Telegram's servers.
3. **No Local Token Storage**: Your local configuration `~/.goalkeeper.json` stores **zero bot tokens**—only your personal `chat_id`.

---

## 🚀 Installation

GoalKeeper is packaged as a standard Python distribution. You can build and install it locally using:

```bash
bash install.sh
```

### 1. Run Automated Integration Setup
Let goalkeeper automatically configure the hook pipelines and crontab entries:
```bash
goalkeeper install
```
This command outputs the detection and installation status for all supported agents:
```
Detected:
✓ Claude Code
✓ Codex
✗ Aider

Installed integrations:
✓ Claude Code
✓ Codex
```

### 2. Configure Telegram
Simply run the setup wizard and paste the Chat ID sent to you by the bot:
```bash
goalkeeper --setup
```

---

## 🆕 Wrapping Hookless Agents (`goalkeeper run`)

For AI coding agents lacking native hook support (e.g., Aider, Gemini CLI, OpenHands), you can wrap execution using:

```bash
goalkeeper run <command> [args...]
```

**Example:**
```bash
goalkeeper run aider --model gemini/gemini-1.5-pro
```
This executes the underlying process, streams outputs to the terminal, and automatically sends completion/failure notifications upon exit.

---

## ⚙️ CLI Usage

### Schedule Manual Alerts
```bash
# Relative reminders
goalkeeper schedule Antigravity 10m
goalkeeper schedule Claude 5h 15m

# Clock-time reminders
goalkeeper schedule Codex at 11:29 PM
```

### Monitor Queue Status
```bash
goalkeeper status
```
Prints all scheduled quota refresh triggers, remaining durations, and target clock times.

### Clear Queue
```bash
goalkeeper clear
```

---

## 🔗 Migration & Contributing
- For upgrading information, see the **[MIGRATION.md](file:///home/trader/goalkeeper-package/MIGRATION.md)** guide.
- Want support for another AI CLI agent or have a feature request? Please raise an issue or submit a pull request on our GitHub Repository:
  👉 **[https://github.com/yuvaraj/goalkeeper-cli](https://github.com/yuvaraj/goalkeeper-cli)**

---

## License
MIT License.
