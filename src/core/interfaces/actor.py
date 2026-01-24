from abc import ABC, abstractmethod
from src.core.domain.content import ContentDraft
from src.core.domain.persona import PersonaMask


class SocialActor(ABC):
    """
    Abstract interface for interacting with the external world.
    Now operates on ContentDraft + PersonaMask.
    """

    @abstractmethod
    def can_act(self, draft: ContentDraft, mask: PersonaMask) -> bool:
        """Check platform-specific rate limits and constraints."""
        pass

    @abstractmethod
    def execute(self, draft: ContentDraft, mask: PersonaMask) -> bool:
        """Perform the action. Returns True if successful."""
        pass