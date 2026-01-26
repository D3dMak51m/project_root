from datetime import datetime, timedelta
from src.core.domain.strategy import StrategicPosture, StrategicMode
from src.core.domain.strategic_memory import StrategicMemory


class HorizonShiftService:
    """
    Pure service. Evaluates accumulated strategic experience to shift the strategic mode.
    Mode changes are slow, inertial, and based on aggregate memory state.
    Implements temporal decay for failures to ensure recoverability.
    """

    def evaluate(
            self,
            posture: StrategicPosture,
            memory: StrategicMemory,
            now: datetime
    ) -> StrategicPosture:

        total_paths = len(memory.paths)
        if total_paths == 0:
            return posture

        # 1. Temporal Filtering (Recent Failures Only)
        # Only consider failures within the last 14 days to allow recovery.
        # This prevents permanent degradation from old history.
        window_days = 14
        cutoff_date = now - timedelta(days=window_days)

        recent_paths = [
            p for p in memory.paths.values()
            if p.last_updated >= cutoff_date
        ]

        if not recent_paths:
            # If no recent activity, drift towards BALANCED (neutral state)
            # or maintain current if already stable.
            # For simplicity, we maintain current unless it's extreme.
            return posture

        # 2. Calculate Health Score (0.0 - 1.0)
        # Driven primarily by abandonment ratios and recent failure density.
        # Confidence influence is capped to avoid feedback loops.

        soft_abandoned_count = sum(1 for p in recent_paths if p.abandonment_level == "soft")
        hard_abandoned_count = sum(1 for p in recent_paths if p.abandonment_level == "hard")
        recent_failures = sum(p.failure_count for p in recent_paths)

        # Normalize counts relative to active paths in window
        active_count = len(recent_paths)
        abandonment_ratio = (soft_abandoned_count + (hard_abandoned_count * 2.0)) / max(1, active_count)
        failure_density = min(1.0, recent_failures / max(1, active_count * 3.0))  # Cap density impact

        # Health Formula:
        # Base 1.0 (Perfect)
        # Minus Abandonment Impact (Heavy weight)
        # Minus Failure Density (Medium weight)
        # Plus Confidence Bonus (Small weight, capped)

        confidence_bonus = (posture.confidence_baseline - 0.5) * 0.2  # Max +/- 0.1 impact

        health = 1.0 - (abandonment_ratio * 0.5) - (failure_density * 0.3) + confidence_bonus
        health = max(0.0, min(1.0, health))

        # 3. Determine Target Mode
        target_mode = StrategicMode.BALANCED

        if health < 0.4:
            target_mode = StrategicMode.TACTICAL
        elif health > 0.85:
            target_mode = StrategicMode.STRATEGIC

        # 4. Apply Inertial Shift
        # Only shift if current mode is different and conditions are strong
        # We don't jump TACTICAL <-> STRATEGIC directly, must go through BALANCED

        new_mode = posture.mode

        if posture.mode == StrategicMode.BALANCED:
            if target_mode == StrategicMode.TACTICAL:
                new_mode = StrategicMode.TACTICAL
            elif target_mode == StrategicMode.STRATEGIC:
                new_mode = StrategicMode.STRATEGIC

        elif posture.mode == StrategicMode.TACTICAL:
            # Harder to leave tactical mode (requires significant health recovery)
            # Hysteresis: Enter at < 0.4, Leave at > 0.6
            if health > 0.6:
                new_mode = StrategicMode.BALANCED

        elif posture.mode == StrategicMode.STRATEGIC:
            # Drop to balanced if health dips
            # Hysteresis: Enter at > 0.85, Leave at < 0.75
            if health < 0.75:
                new_mode = StrategicMode.BALANCED

        if new_mode != posture.mode:
            return posture.update(mode=new_mode)

        return posture