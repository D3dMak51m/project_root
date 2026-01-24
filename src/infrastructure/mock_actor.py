from src.core.interfaces.actor import SocialActor
from src.core.domain.action import ActionProposal

class MockSocialActor(SocialActor):
    def can_act(self, proposal: ActionProposal) -> bool:
        # Always allow in mock, unless rate limited (not impl here)
        return True

    def execute(self, proposal: ActionProposal) -> bool:
        print(f"[MOCK ACTOR] Executing: {proposal.type} -> {proposal.content}")
        return True