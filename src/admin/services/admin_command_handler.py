from uuid import UUID
from datetime import datetime
from src.admin.interfaces.admin_command_handler import AdminCommandHandler
from src.admin.domain.admin_command import AdminCommand
from src.admin.domain.governance_decision import GovernanceDecision


class StaticAdminCommandHandler(AdminCommandHandler):
    """
    Deterministic handler for admin commands.
    Translates commands into decisions without side effects.
    """

    def handle(
            self,
            command: AdminCommand,
            decision_id: UUID,
            issued_at: datetime
    ) -> GovernanceDecision:
        effect = command.payload.copy()
        justification = f"Executed {command.action.value} on {command.scope.value}"

        if command.target_id:
            effect["target_id"] = command.target_id
            justification += f" for target {command.target_id}"

        return GovernanceDecision(
            id=decision_id,
            command_id=command.id,
            action=command.action,
            scope=command.scope,
            justification=justification,
            effect=effect,
            issued_at=issued_at,
            issued_by="static_handler"
        )