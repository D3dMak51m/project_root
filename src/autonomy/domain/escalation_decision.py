from enum import Enum

class EscalationDecision(Enum):
    EXECUTE = "EXECUTE"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    DROP = "DROP"