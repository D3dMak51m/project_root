from enum import Enum

class AutonomyMode(Enum):
    SILENT = "SILENT"
    READY = "READY"
    BLOCKED = "BLOCKED"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"