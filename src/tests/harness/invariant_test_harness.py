import os
import shutil
import tempfile
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4

from src.core.domain.entity import AIHuman
from src.core.domain.identity import Identity
from src.core.domain.behavior import BehaviorState
from src.core.domain.memory import MemorySystem
from src.core.domain.stance import Stance
from src.core.domain.readiness import ActionReadiness
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.core.domain.strategic_context import StrategicContext
from src.core.domain.execution_intent import ExecutionIntent
from src.core.domain.execution_result import ExecutionResult, ExecutionStatus, ExecutionFailureType
from src.core.domain.resource import ResourceCost, StrategicResourceBudget
from src.core.domain.exceptions import BudgetInvariantViolation
from src.core.lifecycle.signals import LifeSignals
from src.core.orchestration.strategic_orchestrator import StrategicOrchestrator
from src.core.time.frozen_time_source import FrozenTimeSource
from src.core.ledger.file_ledger import FileStrategicLedger
from src.core.ledger.file_budget_ledger import FileBudgetLedger
from src.core.persistence.file_backend import FileStrategicStateBackend
from src.core.persistence.budget_backend import FileBudgetBackend
from src.infrastructure.adapters.mock_execution_adapter import MockExecutionAdapter
from src.core.replay.exceptions import ReplayIntegrityError


class FailingExecutionAdapter(MockExecutionAdapter):
    """Adapter that simulates failures."""

    def __init__(self, failure_type: ExecutionFailureType = ExecutionFailureType.ENVIRONMENT):
        self.failure_type = failure_type

    def execute(self, intent: ExecutionIntent) -> ExecutionResult:
        return ExecutionResult(
            status=ExecutionStatus.FAILED,
            timestamp=datetime.now(timezone.utc),
            failure_type=self.failure_type,
            reason="Simulated failure",
            costs={"energy": 1.0}
        )


class InvariantTestHarness:
    def __init__(self):
        self.base_dir = tempfile.mkdtemp()
        self.state_dir = os.path.join(self.base_dir, "state")
        self.budget_file = os.path.join(self.base_dir, "budget.json")
        self.ledger_file = os.path.join(self.base_dir, "ledger.jsonl")
        self.budget_ledger_file = os.path.join(self.base_dir, "budget_ledger.jsonl")

        self.start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.time_source = FrozenTimeSource(self.start_time)
        self.context = StrategicContext("global", None, None, "invariant_test")

        self.human = self._create_human()

    def _create_human(self) -> AIHuman:
        from src.core.domain.persona import PersonaMask
        human = AIHuman(
            id=uuid4(),
            identity=Identity("Test", 30, "N/A", "Bio", [], [], {}),
            state=BehaviorState(100.0, 100.0, 0.0, self.start_time, False),
            memory=MemorySystem([], []),
            stance=Stance({}),
            readiness=ActionReadiness(50.0, 40.0, 80.0),
            intentions=[],
            personas=[],
            strategy=StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED),
            deferred_actions=[],
            created_at=self.start_time
        )
        mask = PersonaMask(
            id=uuid4(), human_id=human.id, platform="test", display_name="TestBot",
            bio="", language="en", tone="neutral", verbosity="medium",
            activity_rate=1.0, risk_tolerance=1.0, posting_hours=list(range(24))
        )
        human.personas.append(mask)
        return human

    def _create_orchestrator(self, adapter=None) -> StrategicOrchestrator:
        return StrategicOrchestrator(
            time_source=self.time_source,
            ledger=FileStrategicLedger(self.ledger_file),
            backend=FileStrategicStateBackend(self.state_dir),
            budget_backend=FileBudgetBackend(self.budget_file),
            budget_ledger=FileBudgetLedger(self.budget_ledger_file),
            execution_adapter=adapter or MockExecutionAdapter()
        )

    def test_budget_rollback_on_failure(self):
        print("TEST: Budget Rollback on Failure")
        adapter = FailingExecutionAdapter()
        orchestrator = self._create_orchestrator(adapter)
        orchestrator.register_context(self.context, self.human)

        # Force an intent and execution
        signals = LifeSignals(10.0, 0.0, 0.0, False, {"topic": (0.8, 0.0)}, [], None)
        orchestrator.tick(self.human, signals)  # Form intention

        self.human.readiness.value = 90.0
        orchestrator.tick(self.human, signals)

        history = orchestrator.budget_ledger.get_history()
        rollback_events = [e for e in history if e.event_type == "BUDGET_ROLLED_BACK"]

        if not rollback_events:
            raise AssertionError("No BUDGET_ROLLED_BACK event found after execution failure")
        print("  PASS: Rollback event detected")

    def test_replay_poisoning(self):
        print("TEST: Replay Poisoning Protection")
        orchestrator = self._create_orchestrator()
        orchestrator.register_context(self.context, self.human)
        orchestrator.tick(self.human, LifeSignals(0, 0, 0, False, {}, [], None))

        with open(self.ledger_file, 'a') as f:
            bad_event = {
                "id": str(uuid4()), "timestamp": datetime.now().isoformat(),
                "event_type": "UNKNOWN_TYPE", "details": {}, "context_key": str(self.context)
            }
            f.write(json.dumps(bad_event) + "\n")

        orchestrator_2 = self._create_orchestrator()

        try:
            orchestrator_2.register_context(self.context, self.human)
        except ReplayIntegrityError:
            print("  PASS: ReplayIntegrityError caught on corrupted event")
            return

        raise AssertionError("Replay did not fail on poisoned ledger")

    def test_budget_invariant_violation(self):
        print("TEST: Budget Invariant Violation (Negative Balance)")
        orchestrator = self._create_orchestrator()

        # Manually set a low budget
        orchestrator._budget = StrategicResourceBudget(
            energy_budget=5.0, attention_budget=5.0, execution_slots=1,
            last_updated=self.start_time
        )

        # Create a cost that exceeds budget
        excessive_cost = ResourceCost(energy_cost=10.0, attention_cost=1.0, execution_slot_cost=1)

        # Attempt reservation directly via manager to bypass evaluate() check
        # This simulates a race condition or logic error where evaluate passes but reserve fails
        try:
            orchestrator.resource_manager.reserve(orchestrator._budget, excessive_cost)
        except BudgetInvariantViolation:
            print("  PASS: BudgetInvariantViolation raised on negative balance")
            return

        raise AssertionError("Budget manager allowed negative balance reservation")

    def cleanup(self):
        shutil.rmtree(self.base_dir)