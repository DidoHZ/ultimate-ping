"""
UltimatePing - Real-time Ping Monitor
Live latency monitoring with statistics, spike detection, and visual display.
"""

import asyncio
import time
import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, List, Optional, Tuple

from network_scanner import tcp_ping


@dataclass
class PingSnapshot:
    """Single ping measurement with timestamp."""

    timestamp: float
    latency_ms: float
    is_timeout: bool


@dataclass
class MonitorStats:
    """Accumulated monitoring statistics."""

    total_pings: int = 0
    successful_pings: int = 0
    timeouts: int = 0
    avg_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0
    jitter_ms: float = 0.0
    current_ms: float = 0.0
    packet_loss_pct: float = 0.0
    spike_count: int = 0
    stability_score: float = 100.0


class PingMonitor:
    """
    Real-time ping monitor with history, spike detection, live statistics,
    and intelligent anomaly detection.
    """

    def __init__(
        self,
        target: str,
        port: int = 80,
        interval: float = 1.0,
        history_size: int = 100,
        spike_threshold: float = 2.0,
    ):
        self.target = target
        self.port = port
        self.interval = interval
        self.spike_threshold = spike_threshold

        self.history: Deque[PingSnapshot] = deque(maxlen=history_size)
        self.stats = MonitorStats()
        self._running = False
        self._callbacks: List[Callable[[PingSnapshot, MonitorStats], None]] = []
        self._anomaly_callbacks: List[Callable] = []

        # Intelligent monitoring
        try:
            from intelligence import IntelligentMonitor
            self._intel_monitor = IntelligentMonitor()
        except Exception:
            self._intel_monitor = None

    def on_update(
        self, callback: Callable[[PingSnapshot, MonitorStats], None]
    ) -> None:
        """Register a callback for each ping update."""
        self._callbacks.append(callback)

    def on_anomaly(self, callback: Callable) -> None:
        """Register a callback for anomaly detection."""
        self._anomaly_callbacks.append(callback)

    async def start(self) -> None:
        """Start monitoring loop."""
        self._running = True
        while self._running:
            snapshot = await self._ping_once()
            self.history.append(snapshot)
            self._update_stats(snapshot)

            # Intelligent anomaly detection
            if self._intel_monitor:
                anomaly = self._intel_monitor.analyze_snapshot(
                    snapshot.latency_ms, snapshot.is_timeout
                )
                if anomaly:
                    for cb in self._anomaly_callbacks:
                        try:
                            cb(anomaly, self.stats)
                        except Exception:
                            pass

            for cb in self._callbacks:
                try:
                    cb(snapshot, self.stats)
                except Exception:
                    pass

            await asyncio.sleep(self.interval)

    def stop(self) -> None:
        """Stop monitoring loop."""
        self._running = False

    async def _ping_once(self) -> PingSnapshot:
        """Perform a single ping measurement."""
        latency = await tcp_ping(self.target, port=self.port, timeout=3.0)
        return PingSnapshot(
            timestamp=time.time(),
            latency_ms=round(latency, 2) if latency > 0 else -1,
            is_timeout=latency < 0,
        )

    def get_anomaly_summary(self) -> str:
        """Get pattern summary from intelligent monitor."""
        if self._intel_monitor:
            return self._intel_monitor.get_pattern_summary()
        return "Intelligent monitoring not available"

    def get_anomaly_recommendations(self) -> list:
        """Get recommendations based on detected anomalies."""
        if self._intel_monitor:
            return self._intel_monitor.get_recommendations()
        return []

    def _update_stats(self, snapshot: PingSnapshot) -> None:
        """Update accumulated statistics."""
        self.stats.total_pings += 1

        if snapshot.is_timeout:
            self.stats.timeouts += 1
        else:
            self.stats.successful_pings += 1
            self.stats.current_ms = snapshot.latency_ms
            self.stats.min_ms = min(self.stats.min_ms, snapshot.latency_ms)
            self.stats.max_ms = max(self.stats.max_ms, snapshot.latency_ms)

        # Calculate from history
        latencies = [
            s.latency_ms for s in self.history if not s.is_timeout
        ]
        if latencies:
            self.stats.avg_ms = round(statistics.mean(latencies), 2)

            if len(latencies) >= 2:
                diffs = [
                    abs(latencies[i] - latencies[i - 1])
                    for i in range(1, len(latencies))
                ]
                self.stats.jitter_ms = round(statistics.mean(diffs), 2)

        # Packet loss
        if self.stats.total_pings > 0:
            self.stats.packet_loss_pct = round(
                (self.stats.timeouts / self.stats.total_pings) * 100, 1
            )

        # Spike detection
        if (
            not snapshot.is_timeout
            and self.stats.avg_ms > 0
            and snapshot.latency_ms > self.stats.avg_ms * self.spike_threshold
        ):
            self.stats.spike_count += 1

        # Stability score (0-100)
        self._calculate_stability()

    def _calculate_stability(self) -> None:
        """Calculate network stability score (0-100)."""
        score = 100.0

        # Penalize packet loss heavily
        score -= self.stats.packet_loss_pct * 3

        # Penalize high jitter
        if self.stats.jitter_ms > 5:
            score -= min(30, self.stats.jitter_ms * 2)

        # Penalize spikes
        if self.stats.total_pings > 0:
            spike_rate = self.stats.spike_count / self.stats.total_pings
            score -= spike_rate * 50

        # Penalize high average latency
        if self.stats.avg_ms > 100:
            score -= min(20, (self.stats.avg_ms - 100) / 10)

        self.stats.stability_score = round(max(0, min(100, score)), 1)

    def get_latency_graph(self, width: int = 60) -> str:
        """Generate ASCII latency graph from history."""
        latencies = [
            s.latency_ms for s in self.history if not s.is_timeout
        ]
        if not latencies:
            return "No data yet..."

        # Use last `width` samples
        samples = latencies[-width:]
        if not samples:
            return "No data yet..."

        min_val = min(samples)
        max_val = max(samples)
        range_val = max_val - min_val if max_val != min_val else 1

        height = 10
        graph_lines = []

        for row in range(height, -1, -1):
            threshold = min_val + (range_val * row / height)
            line = ""
            for val in samples:
                if val >= threshold:
                    if val > self.stats.avg_ms * self.spike_threshold:
                        line += "!"  # Spike
                    elif val > self.stats.avg_ms * 1.3:
                        line += "▓"  # Above average
                    else:
                        line += "█"  # Normal
                else:
                    line += " "
            label = f"{threshold:6.1f}ms"
            graph_lines.append(f"  {label} │{line}│")

        graph_lines.append(f"         └{'─' * len(samples)}┘")
        return "\n".join(graph_lines)

    def get_summary(self) -> str:
        """Get formatted monitoring summary."""
        s = self.stats
        stability_emoji = (
            "🟢" if s.stability_score >= 80
            else "🟡" if s.stability_score >= 50
            else "🔴"
        )

        return f"""
╔══════════════════════════════════════════════════╗
║           PING MONITOR - {self.target:<24}║
╠══════════════════════════════════════════════════╣
║  Current:  {s.current_ms:>8.1f} ms                       ║
║  Average:  {s.avg_ms:>8.1f} ms                       ║
║  Minimum:  {s.min_ms:>8.1f} ms                       ║
║  Maximum:  {s.max_ms:>8.1f} ms                       ║
║  Jitter:   {s.jitter_ms:>8.1f} ms                       ║
║  Loss:     {s.packet_loss_pct:>7.1f}%                        ║
║  Spikes:   {s.spike_count:>8d}                           ║
║  Pings:    {s.total_pings:>8d}                           ║
║  Stability: {stability_emoji} {s.stability_score:>5.1f}/100                   ║
╚══════════════════════════════════════════════════╝
"""


async def quick_monitor(
    target: str,
    duration: float = 30,
    interval: float = 0.5,
) -> MonitorStats:
    """Run a quick monitoring session and return stats."""
    monitor = PingMonitor(target, interval=interval)
    task = asyncio.create_task(monitor.start())

    await asyncio.sleep(duration)
    monitor.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    return monitor.stats


class MultiTargetMonitor:
    """Monitor multiple targets simultaneously."""

    def __init__(self, targets: List[str], interval: float = 1.0):
        self.monitors = {
            target: PingMonitor(target, interval=interval)
            for target in targets
        }

    async def start_all(self) -> None:
        """Start all monitors."""
        tasks = [m.start() for m in self.monitors.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

    def stop_all(self) -> None:
        """Stop all monitors."""
        for m in self.monitors.values():
            m.stop()

    def get_all_stats(self) -> List[Tuple[str, MonitorStats]]:
        """Get stats from all monitors, sorted by latency."""
        results = [(t, m.stats) for t, m in self.monitors.items()]
        return sorted(results, key=lambda x: x[1].avg_ms if x[1].avg_ms > 0 else float("inf"))
