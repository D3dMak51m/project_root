from datetime import datetime, timedelta
from typing import Tuple
from src.core.domain.strategy import StrategicPosture
from src.core.domain.strategic_signals import StrategicSignals
from src.core.domain.strategic_memory import StrategicMemory, PathStatus
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.execution_intent import ExecutionIntent
from src.core.services.path_key import extract_path_key


class StrategyAdaptationService:
    """
    Pure service. Adapts strategic posture and memory based on semantic signals.
    Operates within a specific StrategicContext.
    Implements slow, cumulative learning without direct reactivity.
    """

    def adapt(
            self,
            posture: StrategicPosture,
            memory: StrategicMemory,
            signals: StrategicSignals,
            intent: ExecutionIntent,
            context: StrategicContext,
            now: datetime
    ) -> Tuple[StrategicPosture, StrategicMemory]:

        # 1. Adapt Posture (Global/Slow)
        new_confidence = posture.confidence_baseline + (signals.confidence_delta * 0.1)
        new_confidence = max(0.1, min(1.0, new_confidence))

        risk_delta = signals.risk_reassessment * 0.1
        if risk_delta < 0:
            risk_delta *= 1.5

        new_risk = posture.risk_tolerance + risk_delta
        new_risk = max(0.1, min(0.9, new_risk))

        factor_delta = (signals.persistence_bias - 1.0) * 0.1
        new_persistence = posture.persistence_factor + factor_delta
        new_persistence = max(0.5, min(2.0, new_persistence))

        new_posture = posture.update(
            confidence_baseline=new_confidence,
            risk_tolerance=new_risk,
            persistence_factor=new_persistence
        )

        # 2. Adapt Memory (Context-Scoped)
        path_key = extract_path_key(intent, context)

        current_status = memory.get_status(path_key)
        new_failure_count = current_status.failure_count
        new_abandonment = current_status.abandonment_level
        new_cooldown_until = current_status.cooldown_until

        if signals.outcome_classification == "success":
            # Success clears abandonment and cooldown
            new_failure_count = 0
            new_abandonment = "none"
            new_cooldown_until = None

        elif signals.outcome_classification == "blocked":
            # Policy block -> Hard abandonment immediately
            new_failure_count += 1
            new_abandonment = "hard"
            new_cooldown_until = None  # Hard block is permanent, no cooldown needed

        elif signals.outcome_classification == "hostile_env":
            # Environment failure -> Accumulate towards soft abandonment
            new_failure_count += 1
            if new_failure_count >= 3:
                new_abandonment = "soft"
                # Set cooldown for 24 hours (example duration)
                new_cooldown_until = now + timedelta(hours=24)

        new_status = PathStatus(
            failure_count=new_failure_count,
            last_outcome=signals.outcome_classification,
            abandonment_level=new_abandonment,
            last_updated=now,
            cooldown_until=new_cooldown_until
        )

        new_paths = memory.paths.copy()
        new_paths[path_key] = new_status
        new_memory = StrategicMemory(paths=new_paths)

        return new_posture, new_memory