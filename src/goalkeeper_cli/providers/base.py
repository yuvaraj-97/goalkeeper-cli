from abc import ABC, abstractmethod

class NotificationProvider(ABC):
    @abstractmethod
    def send(self, text: str) -> None:
        """Send a notification message text to the configured provider."""
        pass
