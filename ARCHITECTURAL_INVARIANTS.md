# Architectural Invariants (Stage F.2)

This document defines the non-negotiable rules governing the Strategic AI Core.
Any violation of these invariants is considered a critical system failure.

## 1. Budget Invariants

*   **I1.1: No Execution Without Reservation.**
    An `ExecutionIntent` MUST NOT be passed to an `ExecutionAdapter` unless a corresponding budget reservation has been successfully made via `StrategicResourceManager.reserve()`.

*   **I1.2: Non-Negative Budget.**
    `StrategicResourceBudget` values (energy, attention, slots) MUST NEVER drop below zero. Reservation attempts exceeding available resources MUST be rejected.

*   **I1.3: Rollback Safety.**
    If an execution fails or is rejected, the reserved budget MUST be returned via a `BUDGET_ROLLED_BACK` event.

## 2. Causality Invariants

*   **I2.1: Feedback Latency.**
    `ExecutionResult` from tick `N` MUST be processed in tick `N+1`. It MUST NOT influence the state within the same tick `N`.

*   **I2.2: LifeLoop Authority.**
    `LifeLoop` is the SOLE mutator of `AIHuman` state. Services (Thinking, Strategy, etc.) MUST be pure and return values/deltas only.

*   **I2.3: Orchestrator Authority.**
    `StrategicOrchestrator` is the SOLE owner of the global `StrategicResourceBudget` and the lifecycle of `StrategicContextRuntime`s.

## 3. Replay Invariants

*   **I3.1: Determinism.**
    Given an initial snapshot and an identical sequence of `StrategicEvent`s and `BudgetEvent`s, the reconstructed state MUST be bitwise identical to the original runtime state.

*   **I3.2: Side-Effect Isolation.**
    Replay MUST NOT trigger any external side effects (e.g., API calls, execution adapter calls).

*   **I3.3: Poisoning Protection.**
    The Replay Engine MUST detect and reject corrupted event streams (e.g., invalid JSON, missing fields) deterministically, raising `ReplayIntegrityError`.

## 4. Strategic Invariants

*   **I4.1: Context Isolation.**
    Strategic state (Memory, Trajectories) MUST be strictly scoped to a `StrategicContext`. No cross-contamination between contexts is allowed.

*   **I4.2: Silence Default.**
    The default outcome of any tick MUST be silence (no action). Action requires explicit, multi-stage approval (Readiness -> Intention -> Strategy -> Eligibility -> Commitment -> Budget).