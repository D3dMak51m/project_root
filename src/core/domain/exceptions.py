class BudgetInvariantViolation(Exception):
    """Raised when a budget operation violates core invariants (e.g., negative balance)."""
    pass

class SafetyLimitExceeded(Exception):
    """Raised when a runtime safety limit is exceeded."""
    pass

class PanicMode(Exception):
    """Raised when a critical invariant is violated in fail-fast mode."""
    pass