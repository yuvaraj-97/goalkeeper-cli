import os
import json
from pathlib import Path
from goalkeeper_cli.adapters.base import AgentAdapter
from goalkeeper_cli.core.event import GoalKeeperEvent

class ClaudeAdapter(AgentAdapter):
    @property
    def name(self) -> str:
        return "Claude Code"

    def _get_settings_path(self) -> Path:
        return Path.home() / ".claude" / "settings.json"

    def is_installed(self) -> bool:
        return (Path.home() / ".claude").is_dir()

    def install_hooks(self) -> None:
        settings_path = self._get_settings_path()
        if not settings_path.parent.is_dir():
            return

        settings = {}
        if settings_path.exists():
            try:
                with open(settings_path, "r") as f:
                    settings = json.load(f)
            except Exception:
                pass

        # Sibling notify script resolution inside packaging installation
        import goalkeeper_cli
        notify_script = Path(goalkeeper_cli.__file__).parent / "notify.py"

        hooks = settings.setdefault("hooks", {})
        hooks["SessionStart"] = [{"matcher": "", "hooks": [{"type": "command", "command": f"python3 {notify_script} --source=Claude --event=SessionStart", "async": True}]}]
        hooks["Notification"] = [{"matcher": "", "hooks": [{"type": "command", "command": f"python3 {notify_script} --source=Claude", "async": True}]}]
        hooks["PermissionRequest"] = [{"matcher": "", "hooks": [{"type": "command", "command": f"python3 {notify_script} --source=Claude", "async": True}]}]
        hooks["Stop"] = [{"hooks": [{"type": "command", "command": f"python3 {notify_script} --source=Claude", "async": True}]}]
        hooks["StopFailure"] = [{"hooks": [{"type": "command", "command": f"python3 {notify_script} --source=Claude", "async": True}]}]

        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

    def uninstall_hooks(self) -> None:
        settings_path = self._get_settings_path()
        if not settings_path.exists():
            return

        try:
            with open(settings_path, "r") as f:
                settings = json.load(f)

            if "hooks" in settings:
                hooks = settings["hooks"]
                for key in ["SessionStart", "Notification", "PermissionRequest", "Stop", "StopFailure"]:
                    hooks.pop(key, None)

            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass

    def get_supported_events(self) -> list[str]:
        return ["SessionStart", "PermissionRequest", "Notification", "Stop", "StopFailure"]

    def translate_event(self, native_event: str, payload: dict) -> GoalKeeperEvent:
        event_mapping = {
            "SessionStart": "session_start",
            "PermissionRequest": "permission_required",
            "Notification": "notification",
            "Stop": "task_completed",
            "StopFailure": "task_failed"
        }
        
        event_type = event_mapping.get(native_event, "notification")
        
        # Sift special payload fields to standard formats
        return GoalKeeperEvent(
            source="Claude",
            event_type=event_type,
            payload=payload
        )
