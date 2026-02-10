import pytest
from uuid import uuid4
from datetime import datetime, timezone
from src.world.domain.signal import NormalizedSignal
from src.world.services.target_resolution import RuleBasedTargetResolver


def create_signal(content: str) -> NormalizedSignal:
    return NormalizedSignal(
        signal_id=uuid4(),
        source_id="test",
        received_at=datetime.now(timezone.utc),
        observed_at=datetime.now(timezone.utc),
        content=content,
        metadata={}
    )


def test_resolve_country():
    resolver = RuleBasedTargetResolver()
    sig = create_signal("News from Germany today.")
    binding = resolver.resolve(sig)

    assert binding.country is not None
    assert binding.country.iso_code == "DE"
    assert binding.region.code == "EU"


def test_resolve_entity():
    resolver = RuleBasedTargetResolver()
    sig = create_signal("NASA launched a rocket.")
    binding = resolver.resolve(sig)

    assert len(binding.targets) == 1
    assert binding.targets[0].id == "nasa"
    assert binding.targets[0].type == "organization"


def test_resolve_empty():
    resolver = RuleBasedTargetResolver()
    sig = create_signal("Random noise.")
    binding = resolver.resolve(sig)

    assert binding.country is None
    assert binding.region is None
    assert len(binding.targets) == 0


def test_determinism():
    resolver = RuleBasedTargetResolver()
    sig = create_signal("USA and UN meeting.")

    b1 = resolver.resolve(sig)
    b2 = resolver.resolve(sig)

    assert b1 == b2