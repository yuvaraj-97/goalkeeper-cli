from abc import ABC, abstractmethod
from goalkeeper_cli.core.event import GoalKeeperEvent

class AgentAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def is_installed(self) -> bool:
        """Return True if the target agent CLI is installed on this system."""
        pass

    @abstractmethod
    def install_hooks(self) -> None:
        """Register the goalkeeper hook command configuration inside the target CLI config files."""
        pass

    @abstractmethod
    def uninstall_hooks(self) -> None:
        """Remove the goalkeeper hooks from the target CLI configurations."""
        pass

    @abstractmethod
    def get_supported_events(self) -> list[str]:
        """Return the list of event names supported natively by this agent adapter."""
        pass

    @abstractmethod
    def translate_event(self, native_event: str, payload: dict) -> GoalKeeperEvent:
        """Translate the native hook event and payload to a GoalKeeperEvent."""
        pass
