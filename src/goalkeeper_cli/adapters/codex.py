import os
import json
from pathlib import Path
from goalkeeper_cli.adapters.base import AgentAdapter
from goalkeeper_cli.core.event import GoalKeeperEvent

class CodexAdapter(AgentAdapter):
    @property
    def name(self) -> str:
        return "Codex"

    def _get_hooks_path(self) -> Path:
        return Path.home() / ".codex" / "hooks.json"

    def is_installed(self) -> bool:
        return (Path.home() / ".codex").is_dir()

    def install_hooks(self) -> None:
        hooks_path = self._get_hooks_path()
        if not hooks_path.parent.is_dir():
            return

        import goalkeeper_cli
        notify_script = Path(goalkeeper_cli.__file__).parent / "notify.py"

        codex_hooks = {
            "hooks": {
                "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": f"python3 {notify_script} --source=Codex --event=SessionStart", "async": false}]}],
                "PermissionRequest": [{"matcher": "", "hooks": [{"type": "command", "command": f"python3 {notify_script} --source=Codex --event=PermissionRequest", "async": false}]}],
                "Stop": [{"hooks": [{"type": "command", "command": f"python3 {notify_script} --source=Codex --event=Stop", "async": false}]}]
            }
        }

        with open(hooks_path, "w") as f:
            json.dump(codex_hooks, f, indent=2)

    def uninstall_hooks(self) -> None:
        hooks_path = self._get_hooks_path()
        if hooks_path.exists():
            try:
                os.remove(hooks_path)
            except Exception:
                pass

    def get_supported_events(self) -> list[str]:
        return ["SessionStart", "PermissionRequest", "Stop"]

    def translate_event(self, native_event: str, payload: dict) -> GoalKeeperEvent:
        event_mapping = {
            "SessionStart": "session_start",
            "PermissionRequest": "permission_required",
            "Stop": "task_completed"
        }
        event_type = event_mapping.get(native_event, "notification")
        return GoalKeeperEvent(
            source="Codex",
            event_type=event_type,
            payload=payload
        )
