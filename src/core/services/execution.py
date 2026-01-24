import random
from typing import Optional, List
from datetime import datetime
from src.core.domain.entity import AIHuman
from src.core.domain.action import ActionProposal, ExecutionResult
from src.core.domain.intention import Intention
from src.core.domain.persona import PersonaMask
from src.core.domain.content import ContentDraft
from src.core.interfaces.actor import SocialActor
from src.core.services.composer import ContentComposer


class ExecutionService:
    def __init__(self, actor: SocialActor, composer: ContentComposer):
        self.actor = actor
        self.composer = composer

    def propose_action(self, human: AIHuman, intention: Intention) -> Optional[ActionProposal]:
        """
        Converts an Intention into a concrete Proposal.
        Probabilistic: Most intentions fail to become proposals.
        """
        # 1. Probabilistic Filter (The "Laziness" Factor)
        # Even if I want to, do I really want to bother proposing it?
        # 70% chance to drop the intention at this stage
        if random.random() < 0.7: return None
        if intention.type == "generic_thought": return None

        return ActionProposal.create(
            intention_id=intention.id,
            type="post",
            content=f"Expressing: {intention.content}",
            risk=0.2
        )

    def validate_proposal(self, human: AIHuman, proposal: ActionProposal) -> bool:
        """Validates the proposal against internal state (energy, readiness)."""
        if human.readiness.value < 40.0: return False
        if human.state.energy < proposal.energy_cost: return False
        if human.state.fatigue > 80.0: return False
        return True

    def validate_mask(self, mask: PersonaMask, proposal: ActionProposal, current_time: datetime) -> bool:
        """Validates if the mask can act right now."""
        # 1. Time Check [NEW]
        if current_time.hour not in mask.posting_hours:
            return False

        # 2. Activity Rate Check
        if random.random() > mask.activity_rate:
            return False

        # 3. Risk Tolerance Check
        if proposal.risk_level > mask.risk_tolerance:
            return False

        return True

    def execute_action(self, human: AIHuman, proposal: ActionProposal, mask: PersonaMask) -> ExecutionResult:
        """
        Executes a validated proposal using a specific mask.
        """
        # 1. Compose Content (Mock/Template for Stage 8)
        draft = self.composer.compose(proposal, mask)

        # 2. Execute via Actor
        if not self.actor.can_act(draft, mask):
            return ExecutionResult(success=False)

        success = self.actor.execute(draft, mask)

        if success:
            return ExecutionResult(
                success=True,
                action_taken=proposal,
                energy_cost=proposal.energy_cost,
                readiness_decay=50.0,
                executed_intention_id=proposal.intention_id,
                memory_content=f"I posted as {mask.display_name}: {draft.text}"
            )

        return ExecutionResult(success=False)

    def select_mask(self, masks: List[PersonaMask], proposal: ActionProposal) -> Optional[PersonaMask]:
        """
        Selects the appropriate mask for the proposed action platform.
        """
        # In Stage 7 proposal had "abstract" platform.
        # In Stage 8 we assume proposal might hint platform, or we pick default.
        # For now, simple matching or random valid mask.

        candidates = [m for m in masks if m.platform == proposal.platform or proposal.platform == "abstract"]
        if not candidates:
            return None
        return candidates[0]  # Pick first available for now

    def validate(self, human: AIHuman, proposal: ActionProposal, mask: PersonaMask) -> bool:
        """
        Strict validation logic. Rejects most proposals.
        """
        # 1. Readiness Check
        # Must be at least RESTLESS to act
        if human.readiness.value < 40.0: return False

        # 2. Energy Check
        if human.state.energy < proposal.energy_cost: return False

        # 3. Fatigue Check
        # If too tired, risk of mistake is high -> abort
        if human.state.fatigue > 80.0: return False

        # 4. Platform Constraints
        if not self.actor.can_act(proposal): return False

        # 5. Probabilistic Filter (The "Doubt" Factor)
        # Higher risk = higher chance to abort
        abort_chance = 0.1 + (proposal.risk_level * 0.5)
        if random.random() < abort_chance: return False

        # Mask-specific checks
        if random.random() > mask.activity_rate: return False # Mask activity limit
        if proposal.risk_level > mask.risk_tolerance: return False # Mask risk limit

        return True

    def execute_cycle(self, human: AIHuman) -> ExecutionResult:
        if not human.intentions:
            return ExecutionResult(success=False)

        intention = human.intentions[0]

        # 1. Create Proposal
        proposal = self.propose_action(human, intention)
        if not proposal:
            return ExecutionResult(success=False)

        # 2. Select Persona Mask [NEW]
        mask = self.select_mask(human.personas, proposal)
        if not mask:
            return ExecutionResult(success=False)  # No suitable mask found

        # 3. Validate (now includes mask checks)
        if not self.validate(human, proposal, mask):
            return ExecutionResult(success=False, readiness_decay=5.0)

        # 4. Compose Content [NEW]
        draft = self.composer.compose(proposal, mask)

        # 5. Execute via Actor (using Draft and Mask)
        if not self.actor.can_act(draft, mask):
            return ExecutionResult(success=False)

        success = self.actor.execute(draft, mask)

        if success:
            return ExecutionResult(
                success=True,
                action_taken=proposal,
                energy_cost=proposal.energy_cost,
                readiness_decay=50.0,
                executed_intention_id=intention.id,
                memory_content=f"I posted as {mask.display_name}: {draft.text}"
            )

        return ExecutionResult(success=False)