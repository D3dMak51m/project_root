class SemanticInvariantViolation(Exception):
    """
    Raised when a semantic interpretation violates core invariants,
    such as containing strategic advice, commands, or non-descriptive language.
    """
    pass