from datetime import datetime
from uuid import uuid4
from typing import Optional
from dataclasses import dataclass

from src.core.domain.window import ExecutionWindow
from src.core.domain.commitment import ExecutionCommitment
from src.core.domain.behavior import BehaviorState
from src.core.domain.readiness import ActionReadiness


@dataclass(frozen=True)
class CommitmentResolutionResult:
    commitment: Optional[ExecutionCommitment]
    window_consumed: bool
    reason: str


class CommitmentResolutionService:
    """
    Pure service. Decides if an active ExecutionWindow should crystallize into an ExecutionCommitment.
    This is the final decision point before action.
    """

    def resolve(
            self,
            window: ExecutionWindow,
            state: BehaviorState,
            readiness: ActionReadiness,
            now: datetime
    ) -> CommitmentResolutionResult:

        # 1. Stability Check
        if readiness.value < 55.0:
            return CommitmentResolutionResult(
                commitment=None,
                window_consumed=False,
                reason="Readiness dropped below stability threshold"
            )

        # 2. Confidence Threshold
        required_readiness = 80.0 - (window.confidence * 20.0)
        if readiness.value < required_readiness:
            return CommitmentResolutionResult(
                commitment=None,
                window_consumed=False,
                reason="Readiness insufficient for confidence level"
            )

        # 3. Fatigue Check
        if state.fatigue > 70.0:
            return CommitmentResolutionResult(
                commitment=None,
                window_consumed=False,
                reason="Fatigue spike blocked commitment"
            )

        # 4. Time-based Resolution
        time_left = (window.expires_at - now).total_seconds()

        # Immediate commit for high confidence
        if window.confidence > 0.7:
            return self._create_commitment(window, now, "High confidence immediate commit")

        # Commit on closing window
        if time_left < 2.0:
            return self._create_commitment(window, now, "Window closing commit")

        return CommitmentResolutionResult(
            commitment=None,
            window_consumed=False,
            reason="Waiting for optimal moment"
        )

    def _create_commitment(self, window: ExecutionWindow, now: datetime, reason: str) -> CommitmentResolutionResult:
        commitment = ExecutionCommitment(
            id=uuid4(),
            intention_id=window.intention_id,
            persona_id=window.persona_id,
            origin_window_id=window.id,
            committed_at=now,
            confidence=window.confidence
        )
        return CommitmentResolutionResult(
            commitment=commitment,
            window_consumed=True,
            reason=reason
        )