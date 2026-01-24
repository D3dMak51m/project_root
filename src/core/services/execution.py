import random
from typing import Optional
from src.core.domain.entity import AIHuman
from src.core.domain.action import ActionProposal, ExecutionResult
from src.core.domain.intention import Intention
from src.core.interfaces.actor import SocialActor


class ExecutionService:
    """
    The Gatekeeper. Decides if a Proposal becomes Reality.
    Pure logic, returns result object.
    """

    def __init__(self, actor: SocialActor):
        self.actor = actor

    def propose_action(self, human: AIHuman, intention: Intention) -> Optional[ActionProposal]:
        """
        Converts an Intention into a concrete Proposal.
        Probabilistic: Most intentions fail to become proposals.
        """
        # 1. Probabilistic Filter (The "Laziness" Factor)
        # Even if I want to, do I really want to bother proposing it?
        # 70% chance to drop the intention at this stage
        if random.random() < 0.7:
            return None

        if intention.type == "generic_thought":
            return None

        return ActionProposal.create(
            intention_id=intention.id,
            type="post",
            content=f"Expressing: {intention.content}",
            risk=0.2
        )

    def validate(self, human: AIHuman, proposal: ActionProposal) -> bool:
        """
        Strict validation logic. Rejects most proposals.
        """
        # 1. Readiness Check
        # Must be at least RESTLESS to act
        if human.readiness.value < 40.0:
            return False

        # 2. Energy Check
        if human.state.energy < proposal.energy_cost:
            return False

        # 3. Fatigue Check
        # If too tired, risk of mistake is high -> abort
        if human.state.fatigue > 80.0:
            return False

        # 4. Platform Constraints
        if not self.actor.can_act(proposal):
            return False

        # 5. Probabilistic Filter (The "Doubt" Factor)
        # Higher risk = higher chance to abort
        abort_chance = 0.1 + (proposal.risk_level * 0.5)
        if random.random() < abort_chance:
            return False

        return True

    def execute_cycle(self, human: AIHuman) -> ExecutionResult:
        """
        Attempts to execute the highest priority intention.
        Returns ExecutionResult describing what happened (or didn't).
        """
        if not human.intentions:
            return ExecutionResult(success=False)

        intention = human.intentions[0]

        # Create Proposal (Probabilistic)
        proposal = self.propose_action(human, intention)
        if not proposal:
            return ExecutionResult(success=False)

        # Validate
        if not self.validate(human, proposal):
            # Validation failed -> slight readiness decay (frustration)
            return ExecutionResult(success=False, readiness_decay=5.0)

        # Execute (via Abstract Actor)
        success = self.actor.execute(proposal)

        if success:
            return ExecutionResult(
                success=True,
                action_taken=proposal,
                energy_cost=proposal.energy_cost,
                readiness_decay=50.0,  # Release pressure
                executed_intention_id=intention.id,
                memory_content=f"I acted: {proposal.content}"
            )

        return ExecutionResult(success=False)