import pickle
from typing import Any


def encode_payload(value: Any) -> bytes:
    return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)


def decode_payload(value: bytes) -> Any:
    return pickle.loads(value)
