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
from src.core.domain.intention import Intention
from src.core.domain.commitment import ExecutionCommitment
from src.core.domain.window import ExecutionWindow
from src.core.lifecycle.signals import LifeSignals
from src.core.lifecycle.lifeloop import LifeLoop
from src.core.context.internal import InternalContext
from src.core.orchestration.strategic_orchestrator import StrategicOrchestrator
from src.core.orchestration.strategic_context_runtime import StrategicContextRuntime
from src.core.orchestration.routing_policy import ContextRoutingPolicy
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


class TestRoutingPolicy(ContextRoutingPolicy):
    """Routes all signals to a specific test context."""

    def __init__(self, target_context: StrategicContext):
        self.target_context = target_context

    def resolve(self, signals: LifeSignals, available_contexts: List[StrategicContext]) -> List[StrategicContext]:
        return [self.target_context]


class TestLifeLoop(LifeLoop):
    """
    Test-only LifeLoop that deterministically returns an ExecutionIntent.
    Bypasses internal logic to guarantee an execution attempt for invariant testing.
    """

    def __init__(self, intent_to_return: ExecutionIntent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.intent_to_return = intent_to_return

    def tick(
            self,
            human: AIHuman,
            signals: LifeSignals,
            strategic_context: StrategicContext,
            tick_count: int,
            existing_window: Optional[ExecutionWindow] = None,
            existing_commitment: Optional[ExecutionCommitment] = None,
            last_executed_intent: Optional[ExecutionIntent] = None
    ) -> InternalContext:
        # Return a context with the forced intent
        # We need to populate other fields minimally to satisfy type checker
        return InternalContext(
            identity_summary="Test",
            current_mood="neutral",
            energy_level="high",
            recent_thoughts=[],
            active_intentions_count=0,
            readiness_level="ready",
            readiness_value=100.0,
            world_perception=None,
            execution_intent=self.intent_to_return
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
            execution_adapter=adapter or MockExecutionAdapter(),
            routing_policy=TestRoutingPolicy(self.context)
        )

    def test_budget_rollback_on_failure(self):
        print("TEST: Budget Rollback on Failure")
        adapter = FailingExecutionAdapter()
        orchestrator = self._create_orchestrator(adapter)

        # 1. Create forced intent
        intent = ExecutionIntent(
            id=uuid4(),
            commitment_id=uuid4(),
            intention_id=uuid4(),
            persona_id=self.human.personas[0].id,
            abstract_action="test_fail",
            constraints={},
            created_at=self.time_source.now(),
            reversible=True,
            risk_level=0.1,
            estimated_cost=ResourceCost(energy_cost=10.0, attention_cost=5.0, execution_slot_cost=1)
        )

        # 2. Inject TestLifeLoop into runtime
        test_lifeloop = TestLifeLoop(intent_to_return=intent)
        runtime = StrategicContextRuntime(
            context=self.context,
            lifeloop=test_lifeloop,
            tick_count=0,
            active=True
        )
        # Manually register runtime to bypass standard registration which creates standard LifeLoop
        orchestrator._runtimes[str(self.context)] = runtime

        # 3. Tick Orchestrator
        signals = LifeSignals(0.0, 0.0, 0.0, False, {}, [], None)
        orchestrator.tick(self.human, signals)

        # 4. Verify Rollback Event
        history = orchestrator.budget_ledger.get_history()
        rollback_events = [e for e in history if e.event_type == "BUDGET_ROLLED_BACK"]

        if not rollback_events:
            reserved_events = [e for e in history if e.event_type == "BUDGET_RESERVED"]
            print(f"  DEBUG: Reserved events: {len(reserved_events)}")
            print(f"  DEBUG: Total events: {len(history)}")
            raise AssertionError("No BUDGET_ROLLED_BACK event found after execution failure")

        last_rollback = rollback_events[-1]
        if last_rollback.delta["energy"] != 10.0:
            raise AssertionError(f"Rollback delta mismatch: expected 10.0, got {last_rollback.delta['energy']}")

        print("  PASS: Rollback event detected and verified")

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

        orchestrator._budget = StrategicResourceBudget(
            energy_budget=5.0, attention_budget=5.0, execution_slots=1,
            last_updated=self.start_time
        )

        excessive_cost = ResourceCost(energy_cost=10.0, attention_cost=1.0, execution_slot_cost=1)

        try:
            orchestrator.resource_manager.reserve(orchestrator._budget, excessive_cost)
        except BudgetInvariantViolation:
            print("  PASS: BudgetInvariantViolation raised on negative balance")
            return

        raise AssertionError("Budget manager allowed negative balance reservation")

    def cleanup(self):
        shutil.rmtree(self.base_dir)