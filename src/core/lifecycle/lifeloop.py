from datetime import datetime
from src.core.domain.entity import AIHuman

class LifeLoop:
    def tick(self, human: AIHuman, current_time: datetime) -> None:
        pass