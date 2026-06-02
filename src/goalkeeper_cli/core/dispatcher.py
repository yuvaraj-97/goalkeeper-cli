import os
import json
import re
import time
import datetime
from pathlib import Path
from typing import Optional
from goalkeeper_cli.core.event import GoalKeeperEvent
from goalkeeper_cli.core.config import load_config, load_queue, save_queue, load_state, save_state
from goalkeeper_cli.providers.telegram import TelegramProvider

AUDIT_LOG_DIR = Path.home() / ".goalkeeper"
AUDIT_LOG_PATH = AUDIT_LOG_DIR / "audit.log"

LIMIT_PATTERNS = [
    r'(?:refreshes?|resets?)\s+in\s+(?:(\d+)\s*h\w*\s*)?(?:(\d+)\s*m\w*)?',
    r'try again in\s+(?:(\d+)\s*h\w*\s*)?(?:(\d+)\s*m\w*)?',
    r'usage limit',
    r'rate limit',
    r'quota',
]

def parse_limit_duration(text: str) -> int:
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
    for pattern in LIMIT_PATTERNS[:2]:
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

def add_to_queue(token: str, chat_id: int, timestamp: int, source: str, text: str, proxy_url: Optional[str] = None) -> None:
    queue = load_queue()
    if not proxy_url:
        cfg = load_config()
        proxy_url = cfg.get("telegram_proxy_url")
    # Deduplicate: remove any existing quota alert for this source
    queue = [item for item in queue if not (item.get("source") == source and "quota" in item.get("text", "").lower())]
    queue.append({
        "token": token,
        "chat_id": chat_id,
        "timestamp": timestamp,
        "source": source,
        "text": text,
        "proxy_url": proxy_url
    })
    save_queue(queue)

def schedule_reset_alert(token: str, chat_id: int, seconds: int, source: str, proxy_url: Optional[str] = None) -> tuple[str, str]:
    reset_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    reset_str  = reset_time.strftime("%I:%M %p")
    hrs, mins  = divmod(seconds // 60, 60)
    duration_str = f"{hrs}h {mins}m" if hrs else f"{mins}m"

    target_timestamp = int(time.time() + seconds)
    alert_text = f"⏰ *[{source}] Rate Limit Reset!*\nYour {source} quota has refreshed. You can resume now! 🚀"
    
    add_to_queue(token, chat_id, target_timestamp, source, alert_text, proxy_url)
    return duration_str, reset_str

def check_requires_permission(tool_name: str, tool_input: dict, source: str) -> bool:
    if not tool_input:
        tool_input = {}

    allowed_rules = []
    trusted_workspaces = [str(Path.home()), str(Path.home() / "ID_agent"), str(Path.home() / "MCP_Improvement")]

    if source == "Antigravity":
        agy_path = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"
        if agy_path.exists():
            try:
                with open(agy_path) as f:
                    settings = json.load(f)
                    allowed_rules.extend(settings.get("permissions", {}).get("allow", []))
                    workspaces = settings.get("trustedWorkspaces", [])
                    if workspaces:
                        trusted_workspaces = [str(Path(w).expanduser().resolve()) for w in workspaces]
            except Exception:
                pass
    else:
        claude_path = Path.home() / ".claude" / "settings.json"
        if claude_path.exists():
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

    # 2. File Operations
    target_path = (
        tool_input.get("TargetFile") or 
        tool_input.get("path") or 
        tool_input.get("AbsolutePath") or 
        tool_input.get("SearchPath") or 
        tool_input.get("DirectoryPath")
    )
    
    if target_path:
        try:
            abs_path = str(Path(target_path).expanduser().resolve())
            for workspace in trusted_workspaces:
                if abs_path == workspace or abs_path.startswith(workspace + "/"):
                    return False
        except Exception:
            pass
        return True

    return False

def write_audit_log(event: GoalKeeperEvent) -> None:
    try:
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "source": event.source,
            "event_type": event.event_type,
            "payload": event.payload
        }
        with open(AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass

def dispatch_event(event: GoalKeeperEvent) -> None:
    """Format, schedule, dispatch, and log GoalKeeperEvents."""
    write_audit_log(event)
    
    cfg = load_config()
    token = cfg.get("telegram_bot_token")
    chat_id = cfg.get("telegram_chat_id")
    notify_on_completion = cfg.get("notify_on_completion", False)
    proxy_url = cfg.get("telegram_proxy_url")

    provider = TelegramProvider()
    source = event.source
    payload = event.payload

    if event.event_type == "session_start":
        # Handle SessionStart: schedule proactive refresh alerts
        queue = load_queue()
        already_scheduled = any(item.get("source") == source and "Quota Refresh" in item.get("text", "") for item in queue)
        
        if not already_scheduled:
            duration_seconds = 5 * 3600  # Default 5h for Claude/Antigravity
            if source == "Codex":
                duration_seconds = 3 * 3600
                
            target_timestamp = int(time.time() + duration_seconds)
            alert_text = f"⏰ *[{source}] Quota Refresh!*\nYour {source} usage window from your latest session has refreshed. You can resume at full capacity! 🚀"
            add_to_queue(token, chat_id, target_timestamp, source, alert_text, proxy_url)

    elif event.event_type == "permission_required":
        # Retrieve PreToolUse arguments
        tool_call = payload.get("toolCall") or payload
        tool_name = tool_call.get("name") or payload.get("tool_name", "")
        tool_input = tool_call.get("args") or payload.get("tool_input", {})

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

            msg = f"🔐 *[{source}] Permission Required* — `{tool_name}`{detail}\n\nGo to your terminal to approve or deny."
            provider.send(msg)

    elif event.event_type == "rate_limit_hit":
        candidate_text = json.dumps(payload)
        secs = parse_limit_duration(candidate_text)
        if secs:
            duration_str, reset_str = schedule_reset_alert(token, chat_id, secs, source, proxy_url)
            msg = f"⛔ *[{source}] Rate Limit Hit!*\n{source} has paused due to usage limits.\n\n⏳ Resets in *{duration_str}* (around *{reset_str}*)\nI'll notify you the moment it refreshes."
            provider.send(msg)

    elif event.event_type == "task_completed":
        # Check if rate limits are mentioned inside completion messages (Stop hook payload)
        candidate_text = json.dumps(payload)
        secs = parse_limit_duration(candidate_text)
        if secs:
            # Re-route to rate limit hit logic
            event.event_type = "rate_limit_hit"
            dispatch_event(event)
            return

        if notify_on_completion:
            msg = f"✅ *[{source}] Turn Completed!*\nThe agent has finished its response and is waiting for your input."
            provider.send(msg)

    elif event.event_type == "task_failed":
        stop_reason = payload.get("stop_reason") or payload.get("message", "unknown failure")
        msg = f"⚠️ *[{source}] stopped with an error*\n`{stop_reason}`"
        provider.send(msg)

    elif event.event_type == "notification":
        # Regular notification
        message = payload.get("message", f"{source} needs your attention.")
        notif_type = payload.get("notification_type", "")
        if notif_type != "permission_prompt":
            msg = f"🔔 *[{source}] GoalKeeper Alert*\n`{source.lower()}` is waiting for you:\n\n_{message}_"
            provider.send(msg)
