import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/aihuman_db"
    )

    # Behavior constants
    MAX_ENERGY: float = 100.0
    MAX_ATTENTION: float = 100.0
    MAX_FATIGUE: float = 100.0

    ENERGY_RECOVERY_RATE: float = 5.0  # Units per hour
    ATTENTION_DECAY_RATE: float = 2.0  # Units per hour
    FATIGUE_ACCUMULATION_RATE: float = 1.5  # Units per hour active


settings = Settings()