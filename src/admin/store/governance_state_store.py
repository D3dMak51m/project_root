from typing import Dict, List, Optional
from uuid import UUID
from src.admin.domain.governance_decision import GovernanceDecision
from src.admin.domain.governance_scope import GovernanceScope

class GovernanceStateStore:
    """
    In-memory store for active governance decisions.
    """
    def __init__(self):
        self._decisions: Dict[UUID, GovernanceDecision] = {}
        self._scope_index: Dict[GovernanceScope, List[UUID]] = {}

    def add(self, decision: GovernanceDecision) -> None:
        self._decisions[decision.id] = decision
        if decision.scope not in self._scope_index:
            self._scope_index[decision.scope] = []
        self._scope_index[decision.scope].append(decision.id)

    def get(self, decision_id: UUID) -> Optional[GovernanceDecision]:
        return self._decisions.get(decision_id)

    def list_by_scope(self, scope: GovernanceScope) -> List[GovernanceDecision]:
        ids = self._scope_index.get(scope, [])
        return [self._decisions[id] for id in ids]

    def list_all(self) -> List[GovernanceDecision]:
        return list(self._decisions.values())