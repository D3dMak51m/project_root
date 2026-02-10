from abc import ABC, abstractmethod
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import ExecutionResult
from src.core.domain.actor_policy import ActorPolicy


class Actor(ABC):
    """
    The Executor. Responsible for translating Intent into Reality.
    Operates outside the cognitive core (LifeLoop).
    Has NO will, NO desire, ONLY capability and policy.
    """

    @abstractmethod
    def execute(self, intent: ExecutionIntent, policy: ActorPolicy) -> ExecutionResult:
        """
        Attempt to execute the given intent within the constraints of the policy.

        Execution Flow (STRICT):
        1. Policy Validation (Hard Gate):
           - Check if intent.abstract_action is in policy.allowed_actions
           - Check if intent.risk_level <= policy.max_risk_tolerance
           - Check rate limits
           -> If ANY check fails:
              - Return ExecutionResult(status=REJECTED, failure_type=POLICY)
              - WorldAdapter MUST NOT be called.

        2. Environment Interaction:
           - Only if Policy Validation passes.
           - Call WorldAdapter.perform(...)
           -> If adapter fails/throws:
              - Return ExecutionResult(status=FAILED, failure_type=ENVIRONMENT)

        3. Result Capture:
           - Return ExecutionResult(status=SUCCESS/PARTIAL) based on adapter output.

        Must NOT:
        - Modify the intent
        - Throw unhandled exceptions (should return FAILED result)
        - Mutate AIHuman state directly
        """
        pass