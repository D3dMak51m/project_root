from enum import Enum

class GovernanceScope(Enum):
    GLOBAL = "GLOBAL"
    AUTONOMY = "AUTONOMY"
    ESCALATION = "ESCALATION"
    POLICY = "POLICY"
    INTERACTION = "INTERACTION"