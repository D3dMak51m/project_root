from typing import List
from src.memory.domain.memory_signal import MemorySignal
from src.memory.domain.event_record import EventRecord
from src.memory.domain.counterfactual_event import CounterfactualEvent
from src.memory.domain.strategic_learning_signal import StrategicLearningSignal
from src.core.domain.execution_result import ExecutionStatus, ExecutionFailureType


class LearningExtractor:
    """
    Pure service. Extracts long-term strategic lessons from memory signals and event history.
    """

    def extract(
            self,
            memory_signal: MemorySignal,
            recent_events: List[EventRecord],
            recent_counterfactuals: List[CounterfactualEvent]
    ) -> StrategicLearningSignal:

        # 1. Detect Risk Patterns
        # If recent failures were mostly environment-based, we might need to avoid risk
        env_failures = sum(1 for e in recent_events if
                           e.execution_status == ExecutionStatus.FAILED and e.execution_result and e.execution_result.failure_type == ExecutionFailureType.ENVIRONMENT)
        total_events = len(recent_events)
        avoid_risk = (env_failures / total_events > 0.3) if total_events > 0 else False

        # 2. Detect Policy Pressure
        # High policy conflict density from counterfactuals indicates policy pressure
        policy_pressure = memory_signal.policy_conflict_density > 0.4

        # 3. Detect Governance Deadlock
        # High governance friction + high missed opportunity
        gov_deadlock = (
                memory_signal.governance_friction_index > 0.5 and
                memory_signal.missed_opportunity_pressure > 0.5
        )

        # 4. Reduce Exploration
        # If instability detected or deadlock, reduce exploration
        reduce_exploration = memory_signal.instability_detected or gov_deadlock

        # 5. Calculate Priority Bias
        # If success is recent, slight positive bias.
        # If failure pressure is high, negative bias.
        bias = 0.0
        if memory_signal.recent_success:
            bias += 0.1
        if memory_signal.failure_pressure > 1.0:
            bias -= 0.1
        if gov_deadlock:
            bias -= 0.2

        # Clamp bias
        bias = max(-0.3, min(0.3, bias))

        return StrategicLearningSignal(
            avoid_risk_patterns=avoid_risk,
            reduce_exploration=reduce_exploration,
            policy_pressure_high=policy_pressure,
            governance_deadlock_detected=gov_deadlock,
            long_term_priority_bias=bias
        )