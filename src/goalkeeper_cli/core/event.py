import time

class GoalKeeperEvent:
    def __init__(self, source: str, event_type: str, payload: dict, timestamp: int = None):
        self.source = source
        self.event_type = event_type  # e.g., 'session_start', 'permission_required', etc.
        self.payload = payload or {}
        self.timestamp = timestamp or int(time.time())

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "payload": self.payload
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GoalKeeperEvent':
        return cls(
            source=data.get("source"),
            event_type=data.get("event_type"),
            payload=data.get("payload"),
            timestamp=data.get("timestamp")
        )
