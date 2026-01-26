from typing import Tuple, Union
from src.core.domain.intention import Intention
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.strategic_context import StrategicContext


def extract_path_key(
        intent: Union[Intention, ExecutionIntent],
        context: StrategicContext
) -> Tuple[str, ...]:
    """
    Returns a stable, deterministic strategic path identifier.
    Used consistently across filtering and adaptation.

    Format: (domain, action_type)
    """
    # Determine action type based on object type
    if isinstance(intent, ExecutionIntent):
        action_type = intent.abstract_action
    else:
        # For Intention, use type as proxy for abstract action
        action_type = intent.type

    return (
        context.domain,
        action_type,
    )