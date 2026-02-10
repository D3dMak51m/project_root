from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Identity:
    name: str
    age: int
    gender: str
    biography: str
    languages: List[str]
    interests: List[str]
    traits: Dict[str, int]