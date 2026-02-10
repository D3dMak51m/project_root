"""
SANITY TEST — PRODUCTION ALIGNED
Covers Core Stages C.16 – C.20.1

This test validates:
- Strategic memory (soft/hard abandonment + cooldown)
- Strategic trajectories (creation, stalling, decay)
- Horizon / mode shifts
- Competition constraints
- Cooldown semantics (NOT auto-retry)
- Trajectory-weight-based override logic

IMPORTANT:
Cooldown expiration ≠ automatic retry.
Retry requires sufficient strategic commitment.
"""

import sys
from datetime import datetime, timedelta
from uuid import uuid4

try:
    from src.core.domain.entity import AIHuman
    from src.core.domain.identity import Identity
    from src.core.domain.behavior import BehaviorState
    from src.core.domain.memory import MemorySystem
    from src.core.domain.stance import Stance
    from src.core.domain.readiness import ActionReadiness
    from src.core.domain.intention import Intention
    from src.core.domain.persona import PersonaMask
    from src.core.domain.strategy import StrategicPosture, StrategicMode
    from src.core.domain.strategic_memory import StrategicMemory
    from src.core.domain.strategic_trajectory import (
        StrategicTrajectoryMemory,
        StrategicTrajectory,
        TrajectoryStatus,
    )
    from src.core.domain.strategic_context import StrategicContext
    from src.core.domain.execution_result import (
        ExecutionResult,
        ExecutionStatus,
        ExecutionFailureType,
    )
    from src.core.domain.execution_intent import ExecutionIntent
    from src.core.lifecycle.signals import LifeSignals
    from src.core.lifecycle.lifeloop import LifeLoop
except ImportError:
    print("ERROR: Could not import project modules. Check PYTHONPATH.")
    sys.exit(1)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def create_human() -> AIHuman:
    return AIHuman(
        id=uuid4(),
        identity=Identity("TestSubject", 30, "N/A", "Bio", [], [], {}),
        state=BehaviorState(100.0, 100.0, 0.0, datetime.utcnow(), False),
        memory=MemorySystem([], []),
        stance=Stance({}),
        readiness=ActionReadiness(50.0, 40.0, 80.0),
        intentions=[],
        personas=[
            PersonaMask(
                uuid4(),
                uuid4(),
                "test",
                "Bot",
                "",
                "en",
                "neutral",
                "medium",
                1.0,
                1.0,
                list(range(24)),
            )
        ],
        strategy=StrategicPosture([], 0.5, 0.5, 1.0, StrategicMode.BALANCED),
        deferred_actions=[],
        created_at=datetime.utcnow(),
    )


def header(title: str):
    print(f"\n{'=' * 12} {title} {'=' * 12}")


def dump_state(loop: LifeLoop, human: AIHuman, ctx: StrategicContext):
    mem = loop.strategic_memory_store.load(ctx)
    traj = loop.strategic_trajectory_memory_store.load(ctx)

    print(f"Mode: {human.strategy.mode.value}")
    print("--- Trajectories ---")
    if not traj.trajectories:
        print("  (none)")
    for t in traj.trajectories.values():
        print(f"  [{t.id}] {t.status.value} w={t.commitment_weight:.2f}")

    print("--- Strategic Memory ---")
    if not mem.paths:
        print("  (none)")
    for k, v in mem.paths.items():
        cd = f"cooldown={v.cooldown_until}" if v.cooldown_until else "no cooldown"
        print(f"  {k}: {v.abandonment_level}, failures={v.failure_count}, {cd}")


# ---------------------------------------------------------------------
# Sanity Test
# ---------------------------------------------------------------------

def run():
    print("STARTING CORE SANITY TEST (PRODUCTION-ALIGNED)")

    human = create_human()
    loop = LifeLoop()
    ctx = StrategicContext("global", None, None, "social_media")

    now = datetime(2024, 1, 1, 12, 0, 0)

    # --------------------------------------------------
    header("TICK 1 — SUCCESS CREATES TRAJECTORY")
    # --------------------------------------------------

    intent_post = ExecutionIntent(
        uuid4(), uuid4(), uuid4(), uuid4(),
        "post", {}, now, False, 0.1
    )
    result_ok = ExecutionResult(
        ExecutionStatus.SUCCESS,
        now,
        [],
        {"energy": 5.0},
        {}
    )

    loop.tick(
        human,
        LifeSignals(0, 0, 0, False, {}, [], result_ok),
        now,
        last_executed_intent=intent_post,
    )

    dump_state(loop, human, ctx)

    traj_mem = loop.strategic_trajectory_memory_store.load(ctx)
    assert "social_media" in traj_mem.trajectories
    assert traj_mem.get_trajectory("social_media").status == TrajectoryStatus.ACTIVE

    # --------------------------------------------------
    header("TICK 2–4 — HOSTILE ENV → SOFT ABANDON")
    # --------------------------------------------------

    intent_conn = ExecutionIntent(
        uuid4(), uuid4(), uuid4(), uuid4(),
        "connect", {}, now, False, 0.5
    )

    result_fail = ExecutionResult(
        ExecutionStatus.FAILED,
        now,
        [],
        {},
        {},
        ExecutionFailureType.ENVIRONMENT,
        "network",
    )

    for _ in range(3):
        now += timedelta(hours=1)
        loop.tick(
            human,
            LifeSignals(0, 0, 0, False, {}, [], result_fail),
            now,
            last_executed_intent=intent_conn,
        )

    dump_state(loop, human, ctx)

    mem = loop.strategic_memory_store.load(ctx)
    path_key = ("social_media", "connect")
    status = mem.get_status(path_key)

    assert status.abandonment_level == "soft"
    assert status.cooldown_until is not None

    # --------------------------------------------------
    header("TICK 5 — COOLDOWN ENFORCED")
    # --------------------------------------------------

    blocked = Intention(
        uuid4(),
        "connect",
        "retry",
        5.0,
        now,
        3600,
        {"path": ["social_media", "connect"]},
    )
    human.intentions.append(blocked)

    loop.tick(human, LifeSignals(0, 0, 0, False, {}, []), now)

    assert blocked not in human.intentions
    print("OK: intention suppressed during cooldown")

    # --------------------------------------------------
    header("TICK 6 — COOLDOWN EXPIRED (NO AUTO RETRY)")
    # --------------------------------------------------

    now += timedelta(hours=25)

    retry = Intention(
        uuid4(),
        "connect",
        "retry",
        5.0,
        now,
        3600,
        {"path": ["social_media", "connect"]},
    )
    human.intentions.append(retry)

    loop.tick(human, LifeSignals(0, 0, 0, False, {}, []), now)

    assert retry not in human.intentions
    print("OK: cooldown expiration does NOT auto-allow retry")

    # --------------------------------------------------
    header("TICK 7 — STRATEGIC OVERRIDE VIA FILTER (CORRECT)")
    # --------------------------------------------------

    from src.core.services.strategy_filter import StrategicFilterService

    # Manually reinforce trajectory
    traj = traj_mem.get_trajectory("social_media")
    reinforced = StrategicTrajectory(
        id=traj.id,
        status=TrajectoryStatus.ACTIVE,
        commitment_weight=0.85,  # > override threshold
        created_at=traj.created_at,
        last_updated=now,
    )

    loop.strategic_trajectory_memory_store.save(
        ctx,
        StrategicTrajectoryMemory({traj.id: reinforced}),
    )

    retry2 = Intention(
        uuid4(),
        "connect",
        "retry",
        5.0,
        now,
        3600,
        {"path": ["social_media", "connect"]},
    )

    filter_service = StrategicFilterService()

    decision = filter_service.evaluate(
        intention=retry2,
        posture=human.strategy,
        memory=loop.strategic_memory_store.load(ctx),
        trajectory_memory=loop.strategic_trajectory_memory_store.load(ctx),
        context=ctx,
        now=now,
    )

    assert decision.allow is True, decision.reason
    print("OK: strategic override correctly allowed by StrategicFilter")

    # --------------------------------------------------
    header("TICK 8 — OVERRIDE REQUIRES SUCCESS SIGNAL")

    # Now reinforce trajectory via actual success
    success_retry_intent = ExecutionIntent(
        uuid4(), uuid4(), uuid4(), uuid4(),
        "connect", {}, now, False, 0.2
    )

    success_result = ExecutionResult(
        ExecutionStatus.SUCCESS,
        now,
        [],
        {},
        {}
    )

    loop.tick(
        human,
        LifeSignals(0, 0, 0, False, {}, [], success_result),
        now,
        last_executed_intent=success_retry_intent,
    )

    # Try again
    retry3 = Intention(
        uuid4(),
        "connect",
        "retry-after-success",
        5.0,
        now,
        3600,
        {"path": ["social_media", "connect"]},
    )
    human.intentions.append(retry3)

    loop.tick(human, LifeSignals(0, 0, 0, False, {}, []), now)

    assert retry3 in human.intentions
    print("OK: retry allowed after trajectory success + weight")

    # --------------------------------------------------
    header("SANITY TEST PASSED")
    # --------------------------------------------------


if __name__ == "__main__":
    run()
