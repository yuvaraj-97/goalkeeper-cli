# 🥅 GoalKeeper CLI

GoalKeeper is a persistent, zero-overhead notification layer for AI coding agents. It sends real-time Telegram notifications (and supports future notification backends) for permission prompts, rate limits, task completions, and rolling quota resets across developer command-line interfaces: **Claude Code (`claude`)**, **OpenAI Codex (`codex`)**, and **Google's Antigravity CLI (`agy`)**.

---

## 🏛️ Extensible Architecture

GoalKeeper is designed with a premium, extensible architecture:
1. **Agent Adapters**: All agents conform to the `AgentAdapter` interface, which maps native events to a common event model.
2. **Common Event Model**: Defines unified event objects (`GoalKeeperEvent`) including `session_start`, `permission_required`, `rate_limit_hit`, `quota_refresh`, `task_completed`, and `task_failed`.
3. **Pluggable Notification Providers**: Integrates notifications via `NotificationProvider` backends (e.g. `TelegramProvider`, with future support for Slack, Discord, Pushover, etc.).
4. **Event Dispatcher**: A single centralized dispatch pipeline (`dispatch_event`) to format notifications, schedule quota reset reminders, and log audits.

### 📂 Directory Layout

```
goalkeeper-package/
├── MIGRATION.md
├── README.md
├── install.sh
├── pyproject.toml
├── setup.py
├── src/
│   └── goalkeeper_cli/
│       ├── __init__.py
│       ├── cli.py
│       ├── notify.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── claude.py
│       │   ├── codex.py
│       │   └── antigravity.py
│       ├── core/
│       │   ├── config.py
│       │   ├── dispatcher.py
│       │   ├── event.py
│       │   └── runner.py
│       └── providers/
│           ├── base.py
│           └── telegram.py
└── tests/
    ├── test_adapter_detection.py
    ├── test_event_mapping.py
    ├── test_notification_dispatch.py
    └── test_quota_scheduling.py
```

---

## 🔒 Security & Privacy Architecture

GoalKeeper is designed with a premium, secure user experience that **does not expose the Telegram Bot Token** locally and requires **zero custom bot configuration** by default.

### Key Details:
1. **No Local Token Storage**: When running in the default shared-bot mode, your local configuration `~/.goalkeeper.json` stores **zero bot tokens**—only your personal `chat_id`.
2. **The Hosted Proxy API**: To deliver notifications, goalkeeper sends a POST request containing your Telegram `chat_id` and the raw notification message text to a secure hosted proxy API (`https://api.goalkeeper.dev/notify`). The proxy server appends the secret `TELEGRAM_BOT_TOKEN` and forwards the message to Telegram's servers.
3. **Privacy Choice**:
   - By using the shared bot, you acknowledge that the hosted proxy receives your notification contents and `chat_id`.
   - **For maximum privacy**: If you do not want the hosted proxy to see your notification contents, we strongly recommend configuring a custom Telegram Bot via `@BotFather` or self-hosting your own proxy endpoint (see "Self-Hosting" below).

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

#### 🤖 Non-Interactive / AI Setup
If you are configuring GoalKeeper via an AI agent or automated script, you can completely bypass the interactive setup wizard by writing your settings directly to `~/.goalkeeper.json`:

```json
{
  "telegram_chat_id": 123456789,
  "telegram_bot_token": null,
  "telegram_proxy_url": "https://api.goalkeeper.dev/notify",
  "notify_on_completion": false
}
```

Replace `123456789` with your actual Telegram Chat ID (which you can get instantly by messaging `@GoalKeeperCliBot`). If you want to use your own custom bot, set your token in `"telegram_bot_token"`.

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
- For upgrading information, see the **[MIGRATION.md](MIGRATION.md)** guide.
- Want support for another AI CLI agent or have a feature request? Please raise an issue or submit a pull request on our GitHub Repository:
  👉 **[https://github.com/yuvaraj/goalkeeper-cli](https://github.com/yuvaraj/goalkeeper-cli)**

---

## License
MIT License.
