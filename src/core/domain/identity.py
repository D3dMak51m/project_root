from dataclasses import dataclass, field
from typing import List, Dict
from uuid import UUID, uuid4


@dataclass
class PersonalityTraits:
    openness: int  # 0-100
    conscientiousness: int
    extraversion: int
    agreeableness: int
    neuroticism: int


@dataclass
class Identity:
    name: str
    age: int
    gender: str
    biography: str
    languages: List[str]
    interests: List[str]
    traits: PersonalityTraits
    voice_style: str  # Description of tone/style

    def summary(self) -> str:
        return f"{self.name}, {self.age} y.o. ({self.gender}). {self.biography[:50]}..."