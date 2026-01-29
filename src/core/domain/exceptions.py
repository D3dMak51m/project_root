class BudgetInvariantViolation(Exception):
    """Raised when a budget operation violates core invariants (e.g., negative balance)."""
    pass