from typing import Dict, List
from src.world.interfaces.target_resolver import TargetResolver
from src.world.domain.signal import NormalizedSignal
from src.world.domain.target import TargetBinding, TargetEntity
from src.world.domain.geo import Region, Country


class RuleBasedTargetResolver(TargetResolver):
    """
    Deterministic resolver using static mapping tables.
    No NLP, no LLM.
    """

    def __init__(self):
        # Static configuration for regions
        self._regions = {
            "EU": Region("EU", "Europe"),
            "NA": Region("NA", "North America"),
            "AS": Region("AS", "Asia")
        }

        # Static configuration for countries
        self._countries = {
            "US": Country("US", "United States", self._regions["NA"]),
            "DE": Country("DE", "Germany", self._regions["EU"]),
            "JP": Country("JP", "Japan", self._regions["AS"])
        }

        # Keyword mapping for countries
        self._country_keywords = {
            "usa": self._countries["US"],
            "united states": self._countries["US"],
            "germany": self._countries["DE"],
            "japan": self._countries["JP"]
        }

        # Keyword mapping for entities
        self._entity_keywords = {
            "nasa": TargetEntity("nasa", "organization", "NASA"),
            "un": TargetEntity("un", "organization", "United Nations"),
            "eu": TargetEntity("eu", "organization", "European Union")
        }

    def resolve(self, signal: NormalizedSignal) -> TargetBinding:
        content_lower = signal.content.lower()

        # 1. Resolve Country/Region
        country = None
        region = None

        # Simple keyword matching
        for keyword, c in self._country_keywords.items():
            # Basic word boundary check simulation (in prod use regex)
            if keyword in content_lower:
                country = c
                region = c.region
                break

        # 2. Resolve Targets
        targets = []
        for keyword, entity in self._entity_keywords.items():
            if keyword in content_lower:
                targets.append(entity)

        return TargetBinding(
            signal_id=signal.signal_id,
            region=region,
            country=country,
            targets=targets
        )