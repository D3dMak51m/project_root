from dataclasses import dataclass

@dataclass
class ActionReadiness:
    value: float
    threshold_restless: float
    threshold_ready: float