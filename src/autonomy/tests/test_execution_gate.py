import pytest
from src.autonomy.domain.execution_gate_decision import ExecutionGateDecision
from src.autonomy.domain.final_execution_decision import FinalExecutionDecision
from src.autonomy.services.execution_gate import StandardExecutionGate
from src.core.config.runtime_profile import RuntimeProfile, Environment, SafetyLimits
from src.core.domain.runtime_phase import RuntimePhase


# --- Helpers ---

def create_profile(allow_exec: bool = True) -> RuntimeProfile:
    return RuntimeProfile(Environment.PROD, SafetyLimits(), allow_execution=allow_exec)


# --- Tests ---

def test_gate_determinism():
    gate = StandardExecutionGate()
    decision = FinalExecutionDecision.EXECUTE
    profile = create_profile()
    phase = RuntimePhase.EXECUTION

    d1 = gate.evaluate(decision, profile, phase)
    d2 = gate.evaluate(decision, profile, phase)

    assert d1 == d2
    assert d1 == ExecutionGateDecision.ALLOW


def test_deny_on_drop_decision():
    gate = StandardExecutionGate()
    decision = FinalExecutionDecision.DROP
    profile = create_profile()
    phase = RuntimePhase.EXECUTION

    assert gate.evaluate(decision, profile, phase) == ExecutionGateDecision.DENY


def test_deny_in_replay_phase():
    gate = StandardExecutionGate()
    decision = FinalExecutionDecision.EXECUTE
    profile = create_profile()
    phase = RuntimePhase.REPLAY

    assert gate.evaluate(decision, profile, phase) == ExecutionGateDecision.DENY


def test_deny_when_execution_disabled():
    gate = StandardExecutionGate()
    decision = FinalExecutionDecision.EXECUTE
    profile = create_profile(allow_exec=False)
    phase = RuntimePhase.EXECUTION

    assert gate.evaluate(decision, profile, phase) == ExecutionGateDecision.DENY


def test_allow_when_all_conditions_met():
    gate = StandardExecutionGate()
    decision = FinalExecutionDecision.EXECUTE
    profile = create_profile(allow_exec=True)
    phase = RuntimePhase.EXECUTION

    assert gate.evaluate(decision, profile, phase) == ExecutionGateDecision.ALLOW