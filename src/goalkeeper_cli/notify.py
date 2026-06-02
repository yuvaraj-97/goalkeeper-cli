#!/usr/bin/env python3
"""
GoalKeeper Notification Hook & Queue Manager
Reads hook JSON from stdin, translates events, and dispatches them.
"""
import sys
import json
import time
from pathlib import Path
import datetime
import traceback

from goalkeeper_cli.core.event import GoalKeeperEvent
from goalkeeper_cli.core.dispatcher import dispatch_event
from goalkeeper_cli.core.config import load_config, load_queue, save_queue, load_state, save_state
from goalkeeper_cli.providers.telegram import TelegramProvider

CRASH_LOG_DIR = Path.home() / ".goalkeeper"
CRASH_LOG_PATH = CRASH_LOG_DIR / "goalkeeper_crash.log"

def run_cron_processing():
    queue = load_queue()
    if not queue:
        sys.exit(0)

    current_time = int(time.time())
    kept_queue = []
    
    for item in queue:
        if item.get("timestamp", 0) <= current_time:
            token = item.get("token")
            chat_id = item.get("chat_id")
            text = item.get("text")
            proxy_url = item.get("proxy_url")
            
            # Use TelegramProvider to dispatch alerts securely
            provider = TelegramProvider()
            provider.send_with_config(
                text=text,
                token=token,
                chat_id=chat_id,
                proxy_url=proxy_url
            )
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

def run_manual_schedule(source: str, time_str: str):
    from goalkeeper_cli.core.dispatcher import parse_limit_duration, schedule_reset_alert
    cfg = load_config()
    token = cfg.get("telegram_bot_token")
    chat_id = cfg.get("telegram_chat_id")
    proxy_url = cfg.get("telegram_proxy_url")
    if not chat_id:
        print("❌ Goalkeeper is not configured. Please run `goalkeeper --setup` first.")
        return

    text_lower = time_str.lower().strip()
    secs = None

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

    duration_str, reset_str = schedule_reset_alert(token, chat_id, secs, source, proxy_url)
    print(f"✅ Scheduled *{source}* quota alert.")
    print(f"⏳ Will alert in *{duration_str}* (around *{reset_str}*).")

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
            time_str = " ".join(sys.argv[idx + 2:])
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

    # Wrap to prevent hook blocking CLI on hook errors/crashes
    try:
        # Load hook payload
        try:
            hook_input = json.load(sys.stdin)
        except Exception:
            # Stdin load error — exit cleanly
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

        # Dynamic translation of native events
        from goalkeeper_cli.adapters import get_all_adapters
        matched_adapter = None
        for adapter in get_all_adapters():
            # Check by matching either adapter metadata sources or CLI source params
            if source.lower() in adapter.name.lower() or adapter.name.lower() in source.lower():
                matched_adapter = adapter
                break

        # Sift SessionStart dynamically for Antigravity
        is_session_start = (event == "SessionStart")
        if not is_session_start and source == "Antigravity":
            conv_id = hook_input.get("conversationId")
            if conv_id:
                state = load_state()
                last_conv = state.get("last_antigravity_conv_id")
                if conv_id != last_conv:
                    is_session_start = True
                    state["last_antigravity_conv_id"] = conv_id
                    save_state(state)

        # Standardize and Dispatch Event
        if matched_adapter:
            gk_event = matched_adapter.translate_event(event, hook_input)
            if is_session_start:
                gk_event.event_type = "session_start"
            dispatch_event(gk_event)
        else:
            # Fallback direct translation
            event_type = "notification"
            if event in ("PreToolUse", "BeforeTool", "PermissionRequest"):
                event_type = "permission_required"
            elif event in ("Stop", "StopFailure"):
                event_type = "task_completed"
            
            gk_event = GoalKeeperEvent(
                source=source,
                event_type=event_type,
                payload=hook_input
            )
            if is_session_start:
                gk_event.event_type = "session_start"
            dispatch_event(gk_event)

        # Print appropriate CLI outputs
        if event in ("PreToolUse", "BeforeTool"):
            if source == "Codex":
                print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))
            else:
                print(json.dumps({"decision": "allow"}))
        else:
            print(json.dumps({}))
        sys.exit(0)

    except Exception as e:
        try:
            CRASH_LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CRASH_LOG_PATH, "a") as f:
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
