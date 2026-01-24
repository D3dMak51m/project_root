from datetime import datetime
from src.core.domain.window import ExecutionWindow
from src.core.domain.behavior import BehaviorState
from src.core.domain.readiness import ActionReadiness
from src.core.domain.window_decay import ExecutionWindowDecayResult, WindowDecayOutcome


class ExecutionWindowDecayService:
    """
    Pure service. Evaluates whether an existing ExecutionWindow should persist, decay, or close.
    """

    def evaluate(
            self,
            window: ExecutionWindow,
            state: BehaviorState,
            readiness: ActionReadiness,
            now: datetime
    ) -> ExecutionWindowDecayResult:

        # 1. Time Expiration Check
        if now > window.expires_at:
            return ExecutionWindowDecayResult(
                outcome=WindowDecayOutcome.CLOSE,
                reason="Window expired naturally"
            )

        # 2. Fatigue Collapse Check
        # If fatigue spikes too high, the window collapses immediately.
        if state.fatigue > 75.0:
            return ExecutionWindowDecayResult(
                outcome=WindowDecayOutcome.INVALIDATE,
                reason="Fatigue threshold exceeded"
            )

        # 3. Readiness Drop Check
        # If readiness falls below a critical level, the window closes silently.
        if readiness.value < 50.0:
            return ExecutionWindowDecayResult(
                outcome=WindowDecayOutcome.CLOSE,
                reason="Readiness dropped below minimum"
            )

        # 4. Default Persistence
        return ExecutionWindowDecayResult(
            outcome=WindowDecayOutcome.PERSIST,
            reason="Conditions stable"
        )