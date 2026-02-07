"""Network quality monitoring.

Tracks latency and suggests fallbacks proactively.
"""

import logging
import time
from collections import deque
from enum import Enum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class NetworkQuality(str, Enum):
    """Network quality levels."""

    EXCELLENT = "excellent"
    GOOD = "good"
    DEGRADED = "degraded"
    POOR = "poor"


class NetworkStats(BaseModel):
    """Network statistics for a session."""

    quality: NetworkQuality = NetworkQuality.GOOD
    avg_latency_ms: float = 0
    packet_loss_percent: float = 0
    frames_sent: int = 0
    frames_dropped: int = 0
    last_ping_ms: float = 0


# Thresholds for quality levels (in ms)
LATENCY_THRESHOLDS = {
    NetworkQuality.EXCELLENT: 100,
    NetworkQuality.GOOD: 300,
    NetworkQuality.DEGRADED: 600,
    NetworkQuality.POOR: float("inf"),
}


class NetworkMonitor:
    """Monitors network quality for sessions."""

    def __init__(self, window_size: int = 20) -> None:
        self.window_size = window_size
        self.sessions: dict[str, dict[str, Any]] = {}

    def _get_session_data(self, session_id: str) -> dict[str, Any]:
        """Get or create session monitoring data."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "latencies": deque(maxlen=self.window_size),
                "frames_sent": 0,
                "frames_dropped": 0,
                "last_ping_time": 0,
            }
        return self.sessions[session_id]

    def record_latency(self, session_id: str, latency_ms: float) -> None:
        """Record a latency measurement."""
        data = self._get_session_data(session_id)
        data["latencies"].append(latency_ms)
        data["last_ping_time"] = time.time()

    def record_frame_sent(self, session_id: str) -> None:
        """Record a frame successfully sent."""
        data = self._get_session_data(session_id)
        data["frames_sent"] += 1

    def record_frame_dropped(self, session_id: str) -> None:
        """Record a dropped frame."""
        data = self._get_session_data(session_id)
        data["frames_dropped"] += 1

    def get_stats(self, session_id: str) -> NetworkStats:
        """Get current network statistics."""
        data = self._get_session_data(session_id)
        latencies = list(data["latencies"])

        if not latencies:
            return NetworkStats()

        avg_latency = sum(latencies) / len(latencies)
        last_ping = latencies[-1] if latencies else 0

        total_frames = data["frames_sent"] + data["frames_dropped"]
        loss_percent = (
            (data["frames_dropped"] / total_frames * 100) if total_frames > 0 else 0
        )

        # Determine quality
        quality = NetworkQuality.POOR
        for q, threshold in LATENCY_THRESHOLDS.items():
            if avg_latency <= threshold:
                quality = q
                break

        # Downgrade quality if high packet loss
        if loss_percent > 10:
            quality = NetworkQuality.POOR
        elif loss_percent > 5:
            quality = max(NetworkQuality.DEGRADED, quality, key=lambda x: list(NetworkQuality).index(x))

        return NetworkStats(
            quality=quality,
            avg_latency_ms=round(avg_latency, 1),
            packet_loss_percent=round(loss_percent, 1),
            frames_sent=data["frames_sent"],
            frames_dropped=data["frames_dropped"],
            last_ping_ms=round(last_ping, 1),
        )

    def should_suggest_fallback(self, session_id: str) -> tuple[bool, str | None]:
        """Check if we should proactively suggest fallback.

        Returns (should_suggest, reason).
        """
        stats = self.get_stats(session_id)

        if stats.quality == NetworkQuality.POOR:
            return True, "Network quality is poor. Consider switching to photo mode."

        if stats.quality == NetworkQuality.DEGRADED:
            if stats.packet_loss_percent > 5:
                return True, "Experiencing packet loss. Photo mode may be more stable."

        return False, None

    def cleanup(self, session_id: str) -> None:
        """Cleanup monitoring data for a session."""
        self.sessions.pop(session_id, None)


# Singleton instance
network_monitor = NetworkMonitor()
