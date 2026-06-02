# 🥅 GoalKeeper CLI

GoalKeeper is a persistent, zero-overhead notification agent that sends real-time Telegram alerts for permission prompts, rate limits, and rolling quota resets across developer command-line interfaces: **Claude Code (`claude`)**, **OpenAI Codex (`codex`)**, and **Google's Antigravity CLI (`agy`)**.

---

## 🔒 Security & Privacy Architecture

GoalKeeper is designed with a premium, secure user experience that **does not expose the Telegram Bot Token** and requires **zero custom bot configuration** by default.

### How it works:
1. **The Shared Bot (`@GoalKeeperCliBot`)**: Instead of requiring every user to create a bot via `@BotFather`, users simply start a chat with `@GoalKeeperCliBot`. The bot instantly replies with their private, unique Telegram `chat_id` (e.g., `123456789`).
2. **The Secure Message Proxy**: When sending a notification, goalkeeper sends a POST request containing only the message text and your `chat_id` to your secure proxy API (`https://api.goalkeeper.dev/notify`). The proxy server appends the secret `TELEGRAM_BOT_TOKEN` (hidden safely in the backend environment variables) and forwards the message to Telegram's servers.
3. **No Local Token Storage**: Your local configuration `~/.goalkeeper.json` stores **zero bot tokens**—only your personal `chat_id`.

### Can other users see my notifications?
**Absolutely not.** 
In Telegram's protocol, every message must specify a destination `chat_id` which uniquely identifies the chat session between a specific user and the bot. 
- Telegram routes notifications *only* to the user matching the target `chat_id` in the API call.
- Even though all users send notifications through the same bot, **your notifications are completely private to your Telegram account and can never be intercepted or read by anyone else.**

---

## 🛠️ Self-Hosting the Proxy Server (Serverless)

If you are running your own fork of GoalKeeper, you can host your own proxy backend for free on **Vercel** or **Cloudflare Workers** in under 5 minutes.

### Vercel / Node.js Proxy Endpoint:
Create a file at `api/notify.js` inside a web repository:

```javascript
// api/notify.js
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { chat_id, text } = req.body;
  const token = process.env.TELEGRAM_BOT_TOKEN;

  if (!token) {
    return res.status(500).json({ error: 'Server token configuration missing' });
  }

  try {
    const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chat_id,
        text: text,
        parse_mode: 'Markdown'
      })
    });

    const data = await response.json();
    return res.status(response.status).json(data);
  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}
```

Add your `TELEGRAM_BOT_TOKEN` to your Vercel project environment variables, deploy, and configure your clients by running:
```json
{
  "telegram_proxy_url": "https://your-vercel-domain.vercel.app/api/notify"
}
```

---

## 🚀 Installation

GoalKeeper is packaged as a standard Python distribution. You can install it globally:

```bash
pip install goalkeeper-cli
```

### 1. Run Automated Integration Setup
Let goalkeeper automatically configure the hook pipelines and crontab entries:
```bash
goalkeeper install
```

### 2. Configure Telegram
Simply run the setup wizard and paste the Chat ID sent to you by the bot:
```bash
goalkeeper --setup
```

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

## 🔗 Contributing & Feature Requests
Want support for another AI CLI agent (e.g. Aider, OpenHands) or have a feature request?
Please raise an issue or submit a pull request on our GitHub Repository:
👉 **[https://github.com/yuvaraj/goalkeeper-cli](https://github.com/yuvaraj/goalkeeper-cli)**

---

## License
MIT License.
