from abc import ABC, abstractmethod
from src.core.domain.content import ContentDraft
from src.core.domain.persona import PersonaMask

class SocialActor(ABC):
    @abstractmethod
    def can_act(self, draft: ContentDraft, mask: PersonaMask) -> bool:
        pass

    @abstractmethod
    def execute(self, draft: ContentDraft, mask: PersonaMask) -> bool:
        pass