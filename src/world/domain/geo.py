from dataclasses import dataclass

@dataclass(frozen=True)
class Region:
    """
    Geographical region.
    """
    code: str        # e.g. "EU", "CA", "MEA"
    name: str

@dataclass(frozen=True)
class Country:
    """
    Sovereign state or territory.
    """
    iso_code: str    # e.g. "UZ", "RU", "US"
    name: str
    region: Region