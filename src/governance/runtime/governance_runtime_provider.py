from typing import List
from src.admin.interfaces.governance_service import GovernanceService
from src.governance.runtime.governance_runtime_context import RuntimeGovernanceContext

class GovernanceRuntimeProvider:
    """
    Provider that fetches active governance state and builds a runtime context.
    Ensures a consistent view of governance for a single execution cycle.
    """
    def __init__(self, governance_service: GovernanceService):
        self.governance_service = governance_service

    def get_context(self) -> RuntimeGovernanceContext:
        # Fetch all active decisions
        # In a real system, this might be cached or optimized, but here we fetch fresh.
        decisions = self.governance_service.get_active_decisions()
        return RuntimeGovernanceContext.build(decisions)