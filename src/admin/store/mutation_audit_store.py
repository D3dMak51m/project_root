from typing import List

from src.admin.domain.admin_mutation_audit import AdminMutationAudit


class MutationAuditStore:
    """
    Append-only audit log for admin control-plane mutations.
    """

    def __init__(self):
        self._entries: List[AdminMutationAudit] = []

    def append(self, entry: AdminMutationAudit) -> None:
        self._entries.append(entry)

    def list_recent(self, limit: int = 200) -> List[AdminMutationAudit]:
        if limit <= 0:
            return []
        return self._entries[-limit:]
