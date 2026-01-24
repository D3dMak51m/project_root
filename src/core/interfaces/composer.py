from abc import ABC, abstractmethod
from src.core.domain.action import ActionProposal
from src.core.domain.persona import PersonaMask
from src.core.domain.content import ContentDraft

class ContentComposerInterface(ABC):
    @abstractmethod
    def compose(self, proposal: ActionProposal, mask: PersonaMask) -> ContentDraft:
        pass