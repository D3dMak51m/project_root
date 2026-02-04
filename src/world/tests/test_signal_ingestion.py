import pytest
from datetime import datetime, timezone
from src.world.domain.signal import RawSignal, NormalizedSignal
from src.world.services.signal_ingestion import SignalIngestionService
from src.world.adapters.mock_source import MockSignalSource
from src.world.adapters.basic_normalizer import BasicSignalNormalizer
from src.world.adapters.in_memory_store import InMemorySignalStore


def test_ingestion_flow():
    # Setup
    now = datetime.now(timezone.utc)
    raw_data = [
        RawSignal("test:1", now, "Hello World"),
        RawSignal("test:2", now, {"key": "value"})
    ]

    source = MockSignalSource(raw_data)
    normalizer = BasicSignalNormalizer()
    store = InMemorySignalStore()
    service = SignalIngestionService(source, normalizer, store)

    # Execute
    ingested = service.ingest()

    # Verify
    assert len(ingested) == 2
    assert len(store.list()) == 2

    s1 = ingested[0]
    assert s1.source_id == "test:1"
    assert s1.content == "Hello World"
    assert s1.received_at == now

    s2 = ingested[1]
    assert s2.source_id == "test:2"
    assert s2.content == "{'key': 'value'}"


def test_idempotency_mock_source():
    # Ensure mock source behaves as expected (fetches once)
    source = MockSignalSource([RawSignal("test", datetime.now(timezone.utc), "data")])
    assert len(source.fetch()) == 1
    assert len(source.fetch()) == 0


def test_store_filtering():
    store = InMemorySignalStore()
    t1 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    s1 = NormalizedSignal(uuid4(), "src", t1, t1, "1", {})
    s2 = NormalizedSignal(uuid4(), "src", t2, t2, "2", {})

    store.append(s1)
    store.append(s2)

    # Filter since t1 (should exclude t1 if strict > logic, usually > or >= depends on impl)
    # Implementation uses > since
    results = store.list(since=t1)
    assert len(results) == 1
    assert results[0].content == "2"

    # Filter since t3 (future)
    assert len(store.list(since=t3)) == 0


from uuid import uuid4