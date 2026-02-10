from typing import List
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_decision import GovernanceDecision

class AuditLogStore:
    """
    Append-only log for all admin commands and resulting decisions.
    """
    def __init__(self):
        self._log: List[tuple[AdminCommand, GovernanceDecision]] = []

    def append(self, command: AdminCommand, decision: GovernanceDecision) -> None:
        self._log.append((command, decision))

    def get_history(self) -> List[tuple[AdminCommand, GovernanceDecision]]:
        return list(self._log)