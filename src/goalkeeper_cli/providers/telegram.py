import os
import sys
import json
import subprocess
from typing import Optional, Union
from goalkeeper_cli.providers.base import NotificationProvider
from goalkeeper_cli.core.config import load_config

class TelegramProvider(NotificationProvider):
    def send(self, text: str) -> None:
        cfg = load_config()
        self.send_with_config(
            text=text,
            token=cfg.get("telegram_bot_token"),
            chat_id=cfg.get("telegram_chat_id"),
            proxy_url=cfg.get("telegram_proxy_url", "https://api.goalkeeper.dev/notify")
        )

    def send_with_config(
        self,
        text: str,
        token: Optional[str],
        chat_id: Optional[Union[int, str]],
        proxy_url: Optional[str] = None,
    ) -> None:
        if not chat_id:
            # Not configured — silently ignore
            return

        if not proxy_url:
            proxy_url = "https://api.goalkeeper.dev/notify"

        if not token:
            # Proxy-forwarded mode (Shared Bot)
            url = proxy_url
            payload = {"chat_id": chat_id, "text": text}
        else:
            # Direct Telegram mode (Custom Bot)
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}

        # Spawn detached background process to send Telegram alert asynchronously
        import tempfile
        script_content = (
            "import urllib.request, json, os\n"
            f"url = {repr(url)}\n"
            f"payload = {repr(payload)}\n"
            "data = json.dumps(payload).encode()\n"
            "req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})\n"
            "try:\n"
            "    urllib.request.urlopen(req, timeout=10)\n"
            "except Exception:\n"
            "    pass\n"
            "finally:\n"
            "    try:\n"
            "        os.remove(__file__)\n"
            "    except Exception:\n"
            "        pass\n"
        )
        
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        tmp.write(script_content)
        tmp.flush()
        tmp.close()

        # Detach execution
        subprocess.Popen([sys.executable, tmp.name], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
