import os
import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".goalkeeper.json"
QUEUE_PATH = Path.home() / ".goalkeeper_queue.json"
STATE_PATH = Path.home() / ".goalkeeper_state.json"

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(cfg: dict) -> None:
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

def load_queue() -> list:
    if QUEUE_PATH.exists():
        try:
            with open(QUEUE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_queue(queue: list) -> None:
    try:
        with open(QUEUE_PATH, "w") as f:
            json.dump(queue, f, indent=2)
    except Exception:
        pass

def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state: dict) -> None:
    try:
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass
