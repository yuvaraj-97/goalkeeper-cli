#!/usr/bin/env python3
"""
🥅 GoalKeeper — Telegram notifications for Claude/Codex/Antigravity CLI agents.
Provides commands to manually schedule and monitor quota reset notifications.
"""
import sys
import os
import json
import subprocess
from pathlib import Path

CONFIG_PATH = Path.home() / ".goalkeeper.json"
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTIFY_SCRIPT = os.path.join(PACKAGE_DIR, "notify.py")

def setup_wizard():
    import urllib.request, urllib.error, time
    print("====================================================")
    print("      🥅  GoalKeeper Telegram Setup Wizard  🥅      ")
    print("====================================================")
    print("Select your Telegram Bot option:")
    print("  [1] GoalKeeper Shared Bot (Instant setup, recommended)")
    print("  [2] Custom Bot (Configure your own bot token)")
    mode = input("👉 Select Option [1 or 2, default: 1]: ").strip()

    token = None
    chat_id = None
    proxy_url = "https://api.goalkeeper.dev/notify"  # Default secure proxy URL

    if mode == "2":
        token = input("👉 Enter your Telegram Bot Token: ").strip()
        if not token:
            print("❌ Token cannot be empty.")
            return

        url = f"https://api.telegram.org/bot{token}/getMe"
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                res = json.loads(r.read())
            if not res.get("ok"):
                print("❌ Invalid token.")
                return
            bot_name = res["result"]["first_name"]
            bot_user = res["result"]["username"]
            print(f"✅ Bot verified: {bot_name} (@{bot_user})")
        except Exception as e:
            print(f"❌ Error: {e}")
            return

        print("\nHow would you like to configure your Telegram Chat ID?")
        print("  [1] Auto-detect (Message your bot and goalkeeper will grab it)")
        print("  [2] Enter manually (If you already know your Chat ID)")
        choice = input("👉 Choice [1 or 2, default: 1]: ").strip()

        if choice == "2":
            cid_str = input("👉 Enter your Telegram Chat ID: ").strip()
            if cid_str:
                try:
                    chat_id = int(cid_str)
                except ValueError:
                    print("❌ Invalid Chat ID. Must be an integer number.")
                    return
        else:
            print(f"\n1. Open t.me/{bot_user} in Telegram.")
            print("2. Send any message to the bot (e.g., /start or 'hello').")
            input("3. Once sent, press [Enter] here to start detection...")

            print("🔍 Searching for your chat ID...", end="", flush=True)
            last_err = None
            for _ in range(15):
                try:
                    url2 = f"https://api.telegram.org/bot{token}/getUpdates?offset=-1&timeout=2"
                    with urllib.request.urlopen(url2, timeout=5) as r:
                        data = json.loads(r.read())
                    if data.get("ok") and data.get("result"):
                        msg = data["result"][-1].get("message", {})
                        chat_id = msg.get("chat", {}).get("id")
                        name = msg.get("from", {}).get("first_name", "?")
                        if chat_id:
                            print(f"\n✅ Connected to {name} (ID: {chat_id})")
                            break
                except urllib.error.HTTPError as e:
                    if e.code == 409:
                        print("\n⚠️ Telegram API returned 409 Conflict. Webhook active!")
                        break
                    else:
                        last_err = f"HTTP Error {e.code}: {e.reason}"
                except Exception as e:
                    last_err = str(e)
                time.sleep(1)
                print(".", end="", flush=True)
            print()

        if not chat_id:
            print("❌ Auto-detection failed or timed out.")
            cid_str = input("👉 Enter your Telegram Chat ID manually: ").strip()
            if cid_str:
                try:
                    chat_id = int(cid_str)
                except ValueError:
                    print("❌ Invalid Chat ID.")
                    return
    else:
        # Premium Shared Bot Flow
        print("\n📥 Instant Telegram Setup:")
        print("  1. Open t.me/GoalKeeperCliBot in Telegram.")
        print("  2. Send /start or any message.")
        print("  3. The bot will instantly reply with your Chat ID.")
        print("     (No third-party bots, zero ads, completely secure)")
        
        cid_str = input("\n👉 Enter the Chat ID sent by the bot: ").strip()
        if cid_str:
            try:
                chat_id = int(cid_str)
            except ValueError:
                print("❌ Invalid Chat ID. Must be an integer number.")
                return
        else:
            print("❌ Setup cancelled.")
            return

    # Notification Preference Prompt
    print("\n🔔 Notification Preferences:")
    choice_nc = input("👉 Receive Telegram notifications when a task/prompt response completes? [y/N, default: n]: ").strip().lower()
    notify_on_completion = choice_nc in ("y", "yes")

    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    cfg["telegram_bot_token"] = token
    cfg["telegram_chat_id"] = chat_id
    cfg["telegram_proxy_url"] = proxy_url
    cfg["notify_on_completion"] = notify_on_completion
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"🎉 Saved to {CONFIG_PATH}")

    # Test message
    if not token:
        url3 = proxy_url
        payload = json.dumps({"chat_id": chat_id, "text": "🥅 GoalKeeper connected! Quota alerts will now be sent here."}).encode()
    else:
        url3 = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": "🥅 GoalKeeper connected! Quota alerts will now be sent here.", "parse_mode": "Markdown"}).encode()

    try:
        urllib.request.urlopen(urllib.request.Request(url3, data=payload, headers={"Content-Type": "application/json"}), timeout=8)
        print("📨 Test message sent successfully!")
    except Exception as e:
        print(f"⚠️ Failed to send test message: {e}")

def run_configure(args):
    if not os.path.exists(CONFIG_PATH):
        print("❌ Goalkeeper is not configured. Please run: goalkeeper --setup first.")
        return

    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)

    if not args:
        print("🥅 Current GoalKeeper Settings:")
        for k, v in cfg.items():
            print(f"  {k}: {v}")
        return

    if len(args) < 2:
        print("Usage: goalkeeper config <key> <value>")
        print("Example: goalkeeper config notify_on_completion true")
        return

    key = args[0]
    val_str = args[1].lower().strip()
    
    STANDARD_KEYS = ("telegram_bot_token", "telegram_chat_id", "telegram_proxy_url", "notify_on_completion")
    if key not in cfg and key not in STANDARD_KEYS:
        print(f"⚠️ Warning: '{key}' is not a standard goalkeeper setting, but setting it anyway.")

    if val_str in ("true", "1", "yes", "y"):
        val = True
    elif val_str in ("false", "0", "no", "n"):
        val = False
    else:
        try:
            val = int(val_str)
        except ValueError:
            val = args[1]

    cfg[key] = val
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"🎉 Updated '{key}' to: {val}")

def install_goalkeeper():
    print("🚀 Installing GoalKeeper CLI integrations...")

    # 1. Install Cron Job
    import goalkeeper_cli
    notify_script = Path(goalkeeper_cli.__file__).parent / "notify.py"
    cron_cmd = f"* * * * * python3 {notify_script} --cron"
    try:
        current_cron = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout
        if cron_cmd not in current_cron:
            new_cron = current_cron.rstrip() + f"\n{cron_cmd}\n"
            subprocess.run(["crontab", "-"], input=new_cron, text=True, check=True)
            print("✅ Installed goalkeeper background cron queue checker.")
        else:
            print("ℹ️ Goalkeeper background cron is already installed.")
    except Exception as e:
        print(f"⚠️ Warning: Failed to install cron job: {e}")

    # 2. Load and execute adapters
    from goalkeeper_cli.adapters import get_all_adapters
    adapters = get_all_adapters()

    print("\nDetected:")
    detected = []
    not_detected = []
    
    for adapter in adapters:
        if adapter.is_installed():
            print(f"✓ {adapter.name}")
            detected.append(adapter)
        else:
            print(f"✗ {adapter.name}")
            not_detected.append(adapter)

    # Future compatibility mock/Aider placeholder for install log requirements
    print("✗ Aider")

    print("\nInstalled integrations:")
    installed = []
    for adapter in detected:
        try:
            adapter.install_hooks()
            print(f"✓ {adapter.name}")
            installed.append(adapter)
        except Exception as e:
            print(f"✗ {adapter.name} (failed: {e})")

    print("\n🎉 GoalKeeper CLI successfully installed!")
    print("----------------------------------------------------")
    print("💡 Did you know? GoalKeeper concurrently supports:")
    print("   - Claude Code (Anthropic)")
    print("   - OpenAI Codex (OpenAI)")
    print("   - Antigravity CLI (Google Gemini)")
    print("\n👉 Want support for another AI CLI agent or have a feature request?")
    print("   Please raise an issue or request it on GitHub:")
    print("   🔗 https://github.com/yuvaraj/goalkeeper-cli")
    print("----------------------------------------------------")
    print("\n👉 Next, please run: goalkeeper --setup to configure Telegram.")

def print_help():
    print(""" 🥅 GoalKeeper — Persistent Quota Alert CLI 🥅

Usage:
  goalkeeper install
      Install background cron queue and configure all installed CLI agents (Claude, Codex, Antigravity).

  goalkeeper config [<key> <value>]
      View current preferences, or dynamically toggle setting options.
      Example: goalkeeper config notify_on_completion true

  goalkeeper run <command> [args...]
      Wrap execution of a CLI command lacking hooks (e.g. goalkeeper run aider).

  goalkeeper schedule <source> <duration_or_time>
      Schedule a manual quota reset notification.
      Examples:
          goalkeeper schedule Antigravity 10m
          goalkeeper schedule Claude 5h 15m
          goalkeeper schedule Codex at 11:29 PM

  goalkeeper status / goalkeeper queue
      List all currently queued rate-limit reset notifications.

  goalkeeper clear
      Clear all pending quota reset notifications from the queue.

  goalkeeper --setup
      Run the Telegram bot setup wizard.
""")

def main():
    args = sys.argv[1:]
    if not args:
        print_help()
        sys.exit(0)

    cmd = args[0].lower()
    
    if cmd == "--setup":
        setup_wizard()
    elif cmd == "install":
        install_goalkeeper()
    elif cmd == "config":
        run_configure(args[1:])
    elif cmd == "run":
        from goalkeeper_cli.core.runner import run_command_wrapper
        run_command_wrapper(args[1:])
    elif cmd == "schedule":
        if len(args) < 3:
            print("Usage: goalkeeper schedule <source> <duration_or_time>")
            sys.exit(1)
        source = args[1]
        time_str = " ".join(args[2:])
        # Sibling notify script path resolution
        import goalkeeper_cli
        notify_script = Path(goalkeeper_cli.__file__).parent / "notify.py"
        subprocess.run(["python3", str(notify_script), "--schedule-manual", source, time_str])
    elif cmd in ("status", "queue"):
        import goalkeeper_cli
        notify_script = Path(goalkeeper_cli.__file__).parent / "notify.py"
        subprocess.run(["python3", str(notify_script), "--status"])
    elif cmd == "clear":
        import goalkeeper_cli
        notify_script = Path(goalkeeper_cli.__file__).parent / "notify.py"
        subprocess.run(["python3", str(notify_script), "--clear"])
    else:
        print_help()

if __name__ == "__main__":
    main()
