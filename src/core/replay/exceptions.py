class ReplayIntegrityError(Exception):
    """Raised when event replay encounters an invalid state transition or corrupted data."""
    pass