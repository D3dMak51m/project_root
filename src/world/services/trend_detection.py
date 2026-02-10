from typing import List
from datetime import timedelta
from src.world.interfaces.trend_detector import TrendDetector
from src.world.domain.signal import NormalizedSignal
from src.world.domain.salience import TrendWindow


class RollingWindowTrendDetector(TrendDetector):
    """
    Detects trends using fixed time windows.
    """

    def __init__(self, window_size_seconds: int = 3600):
        self.window_size = timedelta(seconds=window_size_seconds)

    def update(
            self,
            signal: NormalizedSignal,
            current_windows: List[TrendWindow]
    ) -> List[TrendWindow]:

        # Use content hash as key (simple string content for now)
        key = str(hash(signal.content))
        now = signal.received_at

        updated_windows = []
        signal_handled = False

        for window in current_windows:
            # Check if signal fits in this window
            if window.key == key and window.window_start <= now <= window.window_end:
                # Update existing window
                new_count = window.count + 1
                # Delta: simple linear growth rate
                duration = (now - window.window_start).total_seconds()
                delta = new_count / max(1.0, duration)

                updated_windows.append(TrendWindow(
                    key=key,
                    window_start=window.window_start,
                    window_end=window.window_end,
                    count=new_count,
                    delta=delta
                ))
                signal_handled = True
            elif now > window.window_end:
                # Window expired, keep as is (or archive)
                # For this pure function, we return it.
                # Cleanup is caller's responsibility.
                updated_windows.append(window)
            else:
                # Window active but different key
                updated_windows.append(window)

        if not signal_handled:
            # Create new window
            updated_windows.append(TrendWindow(
                key=key,
                window_start=now,
                window_end=now + self.window_size,
                count=1,
                delta=0.0  # Initial delta
            ))

        return updated_windows