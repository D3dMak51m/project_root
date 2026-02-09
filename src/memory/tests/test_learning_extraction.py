import pytest
from uuid import uuid4
from datetime import datetime, timezone

from memory.domain.strategic_learning_signal import StrategicLearningSignal
from src.memory.domain.memory_signal import MemorySignal
from src.memory.domain.event_record import EventRecord
from src.memory.domain.counterfactual_event import CounterfactualEvent
from src.memory.domain.governance_snapshot import GovernanceSnapshot
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType
from src.autonomy.domain.autonomy_state import AutonomyState
from src.autonomy.domain.autonomy_mode import AutonomyMode
from src.interaction.domain.policy_decision import PolicyDecision
from src.memory.services.learning_extractor import LearningExtractor
from src.memory.services.learning_policy_adapter import LearningPolicyAdapter
from src.core.domain.strategy import StrategicPosture, StrategicMode


# --- Helpers ---

def create_event(status: ExecutionStatus,
                 failure_type: ExecutionFailureType = ExecutionFailureType.NONE) -> EventRecord:
    return EventRecord(
        id=uuid4(), intent_id=uuid4(), execution_status=status,
        execution_result=ExecutionResult(status, datetime.now(timezone.utc), failure_type=failure_type),
        autonomy_state_before=AutonomyState(AutonomyMode.READY, "", 0.0, [], False),
        policy_decision=PolicyDecision(True, "", []),
        governance_snapshot=GovernanceSnapshot.empty(),
        issued_at=datetime.now(timezone.utc),
        context_domain="test"
    )


def create_signal(
        failure_pressure=0.0, recent_success=False, instability=False,
        gov_ratio=0.0, missed_opp=0.0, gov_friction=0.0, policy_conflict=0.0
) -> MemorySignal:
    return MemorySignal(
        failure_pressure, recent_success, instability, gov_ratio,
        missed_opp, gov_friction, policy_conflict
    )


# --- Tests ---

def test_learning_extractor_risk_avoidance():
    extractor = LearningExtractor()
    # 4/10 env failures -> >0.3 ratio -> avoid risk
    events = [create_event(ExecutionStatus.FAILED, ExecutionFailureType.ENVIRONMENT) for _ in range(4)] + \
             [create_event(ExecutionStatus.SUCCESS) for _ in range(6)]

    signal = extractor.extract(create_signal(), events, [])
    assert signal.avoid_risk_patterns is True


def test_learning_extractor_deadlock():
    extractor = LearningExtractor()
    # High friction + high missed opportunity
    mem_signal = create_signal(gov_friction=0.6, missed_opp=0.6)

    signal = extractor.extract(mem_signal, [], [])
    assert signal.governance_deadlock_detected is True
    assert signal.reduce_exploration is True
    assert signal.long_term_priority_bias < 0


def test_policy_adapter_risk_reduction():
    adapter = LearningPolicyAdapter()
    posture = StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED)

    # Signal to avoid risk
    # We need to construct a StrategicLearningSignal manually or via extractor
    from src.memory.domain.strategic_learning_signal import StrategicLearningSignal
    signal = StrategicLearningSignal(True, False, False, False, 0.0)

    new_posture = adapter.adapt_posture(posture, signal)
    assert new_posture.risk_tolerance < 0.5


def test_policy_adapter_deadlock_response():
    adapter = LearningPolicyAdapter()
    posture = StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED)

    signal = StrategicLearningSignal(False, True, False, True, -0.2)

    new_posture = adapter.adapt_posture(posture, signal)
    assert new_posture.confidence_baseline < 0.5
    assert new_posture.persistence_factor < 1.0
    assert new_posture.risk_tolerance < 0.5  # Bias applied