from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

class ActorType(Enum):
    STATE = "state"
    ORGANIZATION = "organization"
    GROUP = "group"
    INDIVIDUAL = "individual"
    UNKNOWN = "unknown"

class Sentiment(Enum):
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"

class TimeHorizon(Enum):
    SHORT = "short"
    MID = "mid"
    LONG = "long"

@dataclass(frozen=True)
class Actor:
    name: str
    type: ActorType
    role: str

@dataclass(frozen=True)
class Topic:
    topic: str
    salience: float

@dataclass(frozen=True)
class SemanticInterpretation:
    """
    Structured semantic interpretation of unstructured input.
    Pure data, no strategic advice.
    """
    facts: List[str]
    actors: List[Actor]
    topics: List[Topic]
    sentiment: Sentiment
    uncertainties: List[str]
    time_horizon: TimeHorizon