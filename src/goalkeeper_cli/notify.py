#!/usr/bin/env python3
"""
GoalKeeper Notification Hook & Queue Manager
Reads CLI hook JSON from stdin, sends a Telegram message asynchronously.
Includes a lightweight, persistent, cron-driven queue for quota reset alerts.
"""
import sys
import json
import os
import re
import time
import subprocess
import datetime
import urllib.request

CONFIG_PATH = os.path.expanduser("~/.goalkeeper.json")
QUEUE_PATH = os.path.expanduser("~/.goalkeeper_queue.json")
STATE_PATH = os.path.expanduser("~/.goalkeeper_state.json")

def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state):
    try:
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass

LIMIT_PATTERNS = [
    # "Refreshes in 4h 12m"  or  "resets in 45m"
    r'(?:refreshes?|resets?)\s+in\s+(?:(\d+)\s*h\w*\s*)?(?:(\d+)\s*m\w*)?',
    # "try again in 2h"
    r'try again in\s+(?:(\d+)\s*h\w*\s*)?(?:(\d+)\s*m\w*)?',
    # "usage limit"  → fall back to 5h default
    r'usage limit',
    r'rate limit',
    r'quota',
]

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}

def load_queue():
    if os.path.exists(QUEUE_PATH):
        try:
            with open(QUEUE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_queue(queue):
    try:
        with open(QUEUE_PATH, "w") as f:
            json.dump(queue, f, indent=2)
    except Exception:
        pass

def add_to_queue(token, chat_id, timestamp, source, text):
    queue = load_queue()
    queue.append({
        "token": token,
        "chat_id": chat_id,
        "timestamp": timestamp,
        "source": source,
        "text": text
    })
    save_queue(queue)

def run_cron_processing():
    queue = load_queue()
    if not queue:
        sys.exit(0)

    current_time = int(time.time())
    kept_queue = []
    
    for item in queue:
        if item["timestamp"] <= current_time:
            token = item["token"]
            chat_id = item["chat_id"]
            text = item["text"]
            
            cfg = load_config()
            proxy_url = cfg.get("telegram_proxy_url", "https://api.goalkeeper.dev/notify")
            
            if not token:
                url = proxy_url
                payload = {"chat_id": chat_id, "text": text}
            else:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
                
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            try:
                urllib.request.urlopen(req, timeout=10)
            except Exception:
                pass
        else:
            kept_queue.append(item)
            
    save_queue(kept_queue)
    sys.exit(0)

def run_status():
    queue = load_queue()
    if not queue:
        print("📭 The goalkeeper queue is currently empty.")
        return
    
    print("🥅 Pending Goalkeeper Quota Alerts:")
    current_time = int(time.time())
    for idx, item in enumerate(queue, 1):
        rem = item["timestamp"] - current_time
        if rem <= 0:
            rem_str = "due now"
        else:
            hrs, mins = divmod(rem // 60, 60)
            rem_str = f"in {hrs}h {mins}m" if hrs else f"in {mins}m"
        
        target_time = datetime.datetime.fromtimestamp(item["timestamp"]).strftime("%I:%M %p")
        print(f"  {idx}. [{item['source']}] triggers {rem_str} (at {target_time})")
    print()

def run_clear():
    save_queue([])
    print("🧹 Cleared all goalkeeper quota alerts.")

def run_manual_schedule(source, time_str):
    cfg = load_config()
    token   = cfg.get("telegram_bot_token")
    chat_id = cfg.get("telegram_chat_id")
    if not token or not chat_id:
        print("❌ Goalkeeper is not configured. Please run `goalkeeper --setup` first.")
        return

    text_lower = time_str.lower().strip()
    secs = None

    # Check if absolute time (e.g. "at 11:29 PM", "11:29 PM", "11:29")
    if "at" in text_lower or ":" in text_lower:
        if "at" not in text_lower:
            text_lower = "at " + text_lower
        secs = parse_limit_duration(text_lower)
    else:
        if "in" not in text_lower:
            text_lower = "try again in " + text_lower
        secs = parse_limit_duration(text_lower)

    if not secs or secs <= 0:
        print(f"❌ Could not parse duration/time: '{time_str}'.")
        print("Format examples: '10m', '2h 15m', '11:29 PM', 'at 11:29'")
        return

    duration_str, reset_str = schedule_reset_alert(token, chat_id, secs, source)
    print(f"✅ Scheduled *{source}* quota alert.")
    print(f"⏳ Will alert in *{duration_str}* (around *{reset_str}*).")

def send_async(token, chat_id, text):
    """Send Telegram message asynchronously. Uses a secure proxy endpoint if no token is configured."""
    import tempfile
    
    cfg = load_config()
    proxy_url = cfg.get("telegram_proxy_url", "https://api.goalkeeper.dev/notify")

    if not token:
        # Use secure proxy URL to hide token
        url = proxy_url
        payload_dict = {"chat_id": chat_id, "text": text}
    else:
        # Direct Telegram mode
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload_dict = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}

    script_content = (
        "import urllib.request, json\n"
        f"url = {repr(url)}\n"
        f"payload = {repr(payload_dict)}\n"
        "data = json.dumps(payload).encode()\n"
        "req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})\n"
        "try:\n"
        "    urllib.request.urlopen(req, timeout=10)\n"
        "except Exception:\n"
        "    pass\n"
    )
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
    tmp.write(script_content)
    tmp.flush()
    tmp.close()

    subprocess.Popen([sys.executable, tmp.name], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def parse_limit_duration(text):
    """Return seconds until limit reset, or None if no match."""
    text_lower = text.lower()
    
    # 1. Check for absolute time like "try again at 11:29 PM" or "at 11:29"
    m_abs = re.search(r'(?:(?:try again|resets?|refreshes?)\s+)?at\s+(\d+):(\d+)\s*(am|pm)?', text_lower)
    if m_abs:
        try:
            target_h = int(m_abs.group(1))
            target_m = int(m_abs.group(2))
            ampm = m_abs.group(3)
            
            if ampm == "pm" and target_h < 12:
                target_h += 12
            elif ampm == "am" and target_h == 12:
                target_h = 0
                
            now = datetime.datetime.now()
            current_h = now.hour
            current_m = now.minute
            
            now_minutes = current_h * 60 + current_m
            target_minutes = target_h * 60 + target_m
            
            diff = target_minutes - now_minutes
            if diff <= 0:
                diff += 24 * 60  # resets tomorrow
                
            total = diff * 60
            if total > 0:
                return total
        except Exception:
            pass

    # 2. Check for relative duration like "resets in 45m" or "try again in 2h"
    for pattern in LIMIT_PATTERNS[:2]:  # patterns that capture h/m groups
        m = re.search(pattern, text_lower)
        if m:
            h = int(m.group(1)) if m.group(1) else 0
            mins = int(m.group(2)) if m.group(2) else 0
            total = h * 3600 + mins * 60
            if total > 0:
                return total
                
    # 3. Fallback: message mentions limit keywords but no duration -> 5h default
    for pattern in LIMIT_PATTERNS[2:]:
        if re.search(pattern, text_lower):
            return 5 * 3600
            
    return None

def schedule_reset_alert(token, chat_id, seconds, source="Claude"):
    """Schedule a reset alert in the persistent queue."""
    reset_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    reset_str  = reset_time.strftime("%I:%M %p")
    hrs, mins  = divmod(seconds // 60, 60)
    duration_str = f"{hrs}h {mins}m" if hrs else f"{mins}m"

    target_timestamp = int(time.time() + seconds)
    alert_text = f"⏰ *[{source}] Rate Limit Reset!*\nYour {source} quota has refreshed. You can resume now! 🚀"
    
    add_to_queue(token, chat_id, target_timestamp, source, alert_text)
    
    return duration_str, reset_str

def check_requires_permission(tool_name, tool_input, source="Claude"):
    if not tool_input:
        tool_input = {}

    allowed_rules = []
    trusted_workspaces = ["/home/trader", "/home/trader/ID_agent", "/home/trader/MCP_Improvement"]

    if source == "Antigravity":
        agy_path = os.path.expanduser("~/.gemini/antigravity-cli/settings.json")
        if os.path.exists(agy_path):
            try:
                with open(agy_path) as f:
                    settings = json.load(f)
                    allowed_rules.extend(settings.get("permissions", {}).get("allow", []))
                    workspaces = settings.get("trustedWorkspaces", [])
                    if workspaces:
                        trusted_workspaces = workspaces
            except Exception:
                pass
    else:
        claude_path = os.path.expanduser("~/.claude/settings.json")
        if os.path.exists(claude_path):
            try:
                with open(claude_path) as f:
                    settings = json.load(f)
                    allowed_rules.extend(settings.get("permissions", {}).get("allow", []))
            except Exception:
                pass

    # 1. Shell Commands
    if tool_name in ("run_command", "run_shell_command", "Bash", "exec"):
        cmd = (tool_input.get("CommandLine") or tool_input.get("command") or "").strip()
        if not cmd:
            return False

        if cmd in ("whoami", "date", "pwd", "git status"):
            return False

        for rule in allowed_rules:
            prefix = None
            if rule.startswith("command(") and rule.endswith(")"):
                prefix = rule[8:-1].strip()
            elif rule.startswith("Bash(") and rule.endswith(")"):
                prefix = rule[5:-1].strip()

            if prefix:
                if prefix.endswith(":*"):
                    prefix = prefix[:-2].strip()
                elif prefix.endswith("*"):
                    prefix = prefix[:-1].strip()

                if cmd == prefix or cmd.startswith(prefix + " "):
                    return False
        return True

    # 2. File Reading, Writing, Listing, Searching
    target_path = (
        tool_input.get("TargetFile") or 
        tool_input.get("path") or 
        tool_input.get("AbsolutePath") or 
        tool_input.get("SearchPath") or 
        tool_input.get("DirectoryPath")
    )
    
    if target_path:
        try:
            abs_path = os.path.abspath(os.path.expanduser(target_path))
            for workspace in trusted_workspaces:
                abs_workspace = os.path.abspath(os.path.expanduser(workspace))
                if abs_path == abs_workspace or abs_path.startswith(abs_workspace + "/"):
                    return False
        except Exception:
            pass
        return True

    return False

def main():
    if "--cron" in sys.argv:
        run_cron_processing()
        return

    if "--status" in sys.argv:
        run_status()
        return

    if "--clear" in sys.argv:
        run_clear()
        return

    if "--schedule-manual" in sys.argv:
        try:
            idx = sys.argv.index("--schedule-manual")
            source = sys.argv[idx + 1]
            time_str = sys.argv[idx + 2]
            run_manual_schedule(source, time_str)
        except Exception as e:
            print(f"Error parsing manual schedule: {e}")
        return

    source = "Claude"
    event = ""
    for arg in sys.argv:
        if arg.startswith("--source="):
            source = arg.split("=", 1)[1]
        elif arg.startswith("--event="):
            event = arg.split("=", 1)[1]

    try:
        cfg = load_config()
        token   = cfg.get("telegram_bot_token")
        chat_id = cfg.get("telegram_chat_id")
        
        if not token or not chat_id:
            if event in ("PreToolUse", "BeforeTool"):
                if source == "Codex":
                    print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))
                else:
                    print(json.dumps({"decision": "allow"}))
            else:
                print(json.dumps({}))
            sys.exit(0)

        try:
            hook_input = json.load(sys.stdin)
            with open("/home/trader/.scripts/last_hook_input.json", "w") as df:
                json.dump({"source": source, "event": event, "payload": hook_input}, df, indent=2)
        except Exception as e:
            if event in ("PreToolUse", "BeforeTool"):
                if source == "Codex":
                    print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))
                else:
                    print(json.dumps({"decision": "allow"}))
            else:
                print(json.dumps({}))
            sys.exit(0)

        if not event:
            event = hook_input.get("hook_event_name", "")

        # Check for SessionStart (either native event or dynamic detection)
        is_new_session = (event == "SessionStart")
        
        # Dynamic detection for Antigravity or other hook inputs
        if not is_new_session and source == "Antigravity":
            conv_id = hook_input.get("conversationId")
            if conv_id:
                state = load_state()
                last_conv = state.get("last_antigravity_conv_id")
                if conv_id != last_conv:
                    is_new_session = True
                    state["last_antigravity_conv_id"] = conv_id
                    save_state(state)

        if is_new_session:
            # Schedule proactive quota refresh alert if not already scheduled
            queue = load_queue()
            already_scheduled = any(item["source"] == source and "Quota Refresh" in item["text"] for item in queue)
            
            if not already_scheduled:
                duration_seconds = 5 * 3600  # Default 5h for Claude
                if source == "Codex":
                    duration_seconds = 3 * 3600  # 3h for Codex
                elif source == "Antigravity":
                    duration_seconds = 5 * 3600  # 5h for Antigravity
                    
                target_timestamp = int(time.time() + duration_seconds)
                alert_text = f"⏰ *[{source}] Quota Refresh!*\nYour {source} usage window from your latest session has refreshed. You can resume at full capacity! 🚀"
                
                add_to_queue(token, chat_id, target_timestamp, source, alert_text)
                
            # If native SessionStart event, we print empty JSON and exit
            if event == "SessionStart":
                print(json.dumps({}))
                sys.exit(0)

        # ── PreToolUse / BeforeTool ──
        if event in ("PreToolUse", "BeforeTool"):
            tool_call = hook_input.get("toolCall")
            if not tool_call:
                tool_call = hook_input

            tool_name = tool_call.get("name") or hook_input.get("tool_name", "")
            tool_input = tool_call.get("args") or hook_input.get("tool_input", {})

            if tool_name and check_requires_permission(tool_name, tool_input, source):
                detail = ""
                if "CommandLine" in tool_input or "command" in tool_input:
                    cmd = (tool_input.get("CommandLine") or tool_input.get("command"))[:400]
                    detail = f"\n```\n{cmd}\n```"
                elif "TargetFile" in tool_input:
                    detail = f"\n`{tool_input['TargetFile']}`"
                elif "path" in tool_input:
                    detail = f"\n`{tool_input['path']}`"
                elif "AbsolutePath" in tool_input:
                    detail = f"\n`{tool_input['AbsolutePath']}`"
                elif tool_input:
                    detail = f"\n```\n{json.dumps(tool_input)[:300]}\n```"

                send_async(token, chat_id,
                           f"🔐 *[{source}] Permission Required* — `{tool_name}`{detail}\n\n"
                           f"Go to your terminal to approve or deny.")
            
            if source == "Codex":
                print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))
            else:
                print(json.dumps({"decision": "allow"}))
            sys.exit(0)

        # ── PermissionRequest ──
        elif event == "PermissionRequest":
            tool       = hook_input.get("tool_name") or hook_input.get("tool") or "unknown tool"
            tool_input = hook_input.get("tool_input") or hook_input.get("args") or {}
            description = tool_input.get("description", "")

            detail = ""
            if "command" in tool_input or "CommandLine" in tool_input:
                cmd = (tool_input.get("command") or tool_input.get("CommandLine"))[:400]
                detail = f"\n```\n{cmd}\n```"
                if description:
                    detail += f"\n_{description}_"
            elif "path" in tool_input:
                detail = f"\n`{tool_input['path']}`"
                if description:
                    detail += f"\n_{description}_"
            elif tool_input:
                detail = f"\n```\n{json.dumps(tool_input)[:300]}\n```"

            send_async(token, chat_id,
                       f"🔐 *[{source}] Permission Required* — `{tool}`{detail}\n\n"
                       f"Go to your terminal to approve or deny.")

        # ── Notification ──
        elif event == "Notification":
            message    = hook_input.get("message", f"{source} needs your attention.")
            notif_type = hook_input.get("notification_type", "")
            if notif_type != "permission_prompt":
                send_async(token, chat_id,
                           f"🔔 *[{source}] GoalKeeper Alert*\n`{source.lower()}` is waiting for you:\n\n_{message}_")

        # ── Stop / StopFailure ──
        elif event in ("Stop", "StopFailure"):
            is_error = hook_input.get("is_error", False)
            candidate_text = json.dumps(hook_input)
            
            secs = parse_limit_duration(candidate_text)
            if secs:
                duration_str, reset_str = schedule_reset_alert(token, chat_id, secs, source)
                send_async(token, chat_id,
                           f"⛔ *[{source}] Rate Limit Hit!*\n"
                           f"{source} has paused due to usage limits.\n\n"
                           f"⏳ Resets in *{duration_str}* (around *{reset_str}*)\n"
                           f"I'll notify you the moment it refreshes.")
            elif is_error:
                stop_reason = hook_input.get("stop_reason", "unknown")
                send_async(token, chat_id,
                           f"⚠️ *[{source}] stopped with an error*\n`{stop_reason}`")

        print(json.dumps({}))
        sys.exit(0)

    except Exception as e:
        import traceback
        try:
            with open("/home/trader/.scripts/goalkeeper_crash.log", "a") as f:
                f.write(f"--- Crash at {datetime.datetime.now()} (source={source}, event={event}) ---\n")
                traceback.print_exc(file=f)
        except Exception:
            pass

        if event in ("PreToolUse", "BeforeTool"):
            if source == "Codex":
                print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))
            else:
                print(json.dumps({"decision": "allow"}))
        else:
            print(json.dumps({}))
        sys.exit(0)

if __name__ == "__main__":
    main()
