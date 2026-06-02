import os
import json
from pathlib import Path
from goalkeeper_cli.adapters.base import AgentAdapter
from goalkeeper_cli.core.event import GoalKeeperEvent

class AntigravityAdapter(AgentAdapter):
    @property
    def name(self) -> str:
        return "Antigravity CLI"

    def _get_config_dir(self) -> Path:
        return Path.home() / ".gemini" / "config"

    def is_installed(self) -> bool:
        return (Path.home() / ".gemini").is_dir()

    def install_hooks(self) -> None:
        config_dir = self._get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        hooks_path = config_dir / "hooks.json"

        import goalkeeper_cli
        notify_script = Path(goalkeeper_cli.__file__).parent / "notify.py"

        gemini_hooks = {
            "hooks": {
                "PreToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": f"python3 {notify_script} --source=Antigravity --event=PreToolUse", "async": false}]}],
                "Stop": [{"hooks": [{"type": "command", "command": f"python3 {notify_script} --source=Antigravity --event=Stop", "async": true}]}]
            }
        }

        with open(hooks_path, "w") as f:
            json.dump(gemini_hooks, f, indent=2)

        # Handle active path configuration symlink safely
        cli_dir = Path.home() / ".gemini" / "antigravity-cli"
        if cli_dir.is_dir():
            sym_path = cli_dir / "hooks.json"
            try:
                if sym_path.exists() or sym_path.is_symlink():
                    sym_path.unlink()
                sym_path.symlink_to(hooks_path)
            except Exception:
                pass

    def uninstall_hooks(self) -> None:
        hooks_path = self._get_config_dir() / "hooks.json"
        if hooks_path.exists():
            try:
                hooks_path.unlink()
            except Exception:
                pass

        cli_dir = Path.home() / ".gemini" / "antigravity-cli"
        if cli_dir.is_dir():
            sym_path = cli_dir / "hooks.json"
            try:
                if sym_path.exists() or sym_path.is_symlink():
                    sym_path.unlink()
            except Exception:
                pass

    def get_supported_events(self) -> list[str]:
        return ["PreToolUse", "Stop"]

    def translate_event(self, native_event: str, payload: dict) -> GoalKeeperEvent:
        event_mapping = {
            "PreToolUse": "permission_required",
            "Stop": "task_completed"
        }
        event_type = event_mapping.get(native_event, "notification")
        return GoalKeeperEvent(
            source="Antigravity",
            event_type=event_type,
            payload=payload
        )
