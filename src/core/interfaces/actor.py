from abc import ABC, abstractmethod
from src.core.domain.action import ActionProposal


class SocialActor(ABC):
    """
    Abstract interface for interacting with the external world.
    Implementations (Stage 8+) will handle API calls.
    """

    @abstractmethod
    def can_act(self, proposal: ActionProposal) -> bool:
        """Check platform-specific rate limits and constraints."""
        pass

    @abstractmethod
    def execute(self, proposal: ActionProposal) -> bool:
        """Perform the action. Returns True if successful."""
        pass