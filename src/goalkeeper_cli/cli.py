#!/usr/bin/env python3
"""
🥅 GoalKeeper — Telegram notifications for Claude/Codex/Antigravity CLI agents.
Provides commands to manually schedule and monitor quota reset notifications.
"""
import sys
import os
import json
import subprocess

CONFIG_PATH = os.path.expanduser("~/.goalkeeper.json")
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
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    cfg["telegram_bot_token"] = token
    cfg["telegram_chat_id"] = chat_id
    cfg["telegram_proxy_url"] = proxy_url
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

def install_goalkeeper():
    print("🚀 Installing GoalKeeper CLI integrations...")

    # 1. Install Cron Job
    cron_cmd = f"* * * * * python3 {NOTIFY_SCRIPT} --cron"
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

    # 2. Configure Claude Hooks
    claude_path = os.path.expanduser("~/.claude/settings.json")
    if os.path.exists(claude_path):
        try:
            with open(claude_path, "r") as f:
                settings = json.load(f)
            
            hooks = settings.setdefault("hooks", {})
            hooks["SessionStart"] = [{"matcher": "", "hooks": [{"type": "command", "command": f"python3 {NOTIFY_SCRIPT} --source=Claude --event=SessionStart", "async": true}]}]
            hooks["Notification"] = [{"matcher": "", "hooks": [{"type": "command", "command": f"python3 {NOTIFY_SCRIPT} --source=Claude", "async": true}]}]
            hooks["PermissionRequest"] = [{"matcher": "", "hooks": [{"type": "command", "command": f"python3 {NOTIFY_SCRIPT} --source=Claude", "async": true}]}]
            hooks["Stop"] = [{"hooks": [{"type": "command", "command": f"python3 {NOTIFY_SCRIPT} --source=Claude", "async": true}]}]
            hooks["StopFailure"] = [{"hooks": [{"type": "command", "command": f"python3 {NOTIFY_SCRIPT} --source=Claude", "async": true}]}]

            with open(claude_path, "w") as f:
                json.dump(settings, f, indent=2)
            print("✅ Configured Claude Code hooks (~/.claude/settings.json).")
        except Exception as e:
            print(f"⚠️ Warning: Failed to configure Claude hooks: {e}")
    else:
        print("ℹ️ Claude Code configuration directory not found. Skipping.")

    # 3. Configure Codex Hooks
    codex_dir = os.path.expanduser("~/.codex")
    if os.path.exists(codex_dir):
        try:
            codex_hooks_path = os.path.join(codex_dir, "hooks.json")
            codex_hooks = {
                "hooks": {
                    "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": f"python3 {NOTIFY_SCRIPT} --source=Codex --event=SessionStart", "async": false}]}],
                    "PermissionRequest": [{"matcher": "", "hooks": [{"type": "command", "command": f"python3 {NOTIFY_SCRIPT} --source=Codex --event=PermissionRequest", "async": false}]}],
                    "Stop": [{"hooks": [{"type": "command", "command": f"python3 {NOTIFY_SCRIPT} --source=Codex --event=Stop", "async": false}]}]
                }
            }
            with open(codex_hooks_path, "w") as f:
                json.dump(codex_hooks, f, indent=2)
            print("✅ Configured Codex hooks (~/.codex/hooks.json).")
        except Exception as e:
            print(f"⚠️ Warning: Failed to configure Codex hooks: {e}")
    else:
        print("ℹ️ Codex configuration directory not found. Skipping.")

    # 4. Configure Antigravity Hooks
    gemini_dir = os.path.expanduser("~/.gemini")
    if os.path.exists(gemini_dir):
        try:
            config_dir = os.path.join(gemini_dir, "config")
            os.makedirs(config_dir, exist_ok=True)
            hooks_path = os.path.join(config_dir, "hooks.json")
            
            gemini_hooks = {
                "hooks": {
                    "PreToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": f"python3 {NOTIFY_SCRIPT} --source=Antigravity --event=PreToolUse", "async": false}]}],
                    "Stop": [{"hooks": [{"type": "command", "command": f"python3 {NOTIFY_SCRIPT} --source=Antigravity --event=Stop", "async": true}]}]
                }
            }
            with open(hooks_path, "w") as f:
                json.dump(gemini_hooks, f, indent=2)

            # symlink for active path configuration
            cli_dir = os.path.join(gemini_dir, "antigravity-cli")
            if os.path.exists(cli_dir):
                sym_path = os.path.join(cli_dir, "hooks.json")
                if not os.path.exists(sym_path):
                    os.symlink(hooks_path, sym_path)
            print("✅ Configured Antigravity hooks (~/.gemini/config/hooks.json).")
        except Exception as e:
            print(f"⚠️ Warning: Failed to configure Antigravity hooks: {e}")
    else:
        print("ℹ️ Antigravity configuration directory not found. Skipping.")

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
    elif cmd == "schedule":
        if len(args) < 3:
            print("Usage: goalkeeper schedule <source> <duration_or_time>")
            sys.exit(1)
        source = args[1]
        time_str = " ".join(args[2:])
        subprocess.run(["python3", NOTIFY_SCRIPT, "--schedule-manual", source, time_str])
    elif cmd in ("status", "queue"):
        subprocess.run(["python3", NOTIFY_SCRIPT, "--status"])
    elif cmd == "clear":
        subprocess.run(["python3", NOTIFY_SCRIPT, "--clear"])
    else:
        print_help()

if __name__ == "__main__":
    main()
