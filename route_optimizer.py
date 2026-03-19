"""
UltimatePing - Route Optimizer
Traces network routes, finds optimal paths, and provides multi-path analysis.
"""

import asyncio
import re
import platform
import statistics
from dataclasses import dataclass
from typing import List, Optional, Tuple

from config import OptimizationConfig
from network_scanner import tcp_ping


@dataclass
class RouteHop:
    """A single hop in a traceroute."""

    hop_number: int
    ip: Optional[str]
    hostname: Optional[str]
    latency_ms: float
    is_reachable: bool


@dataclass
class RouteAnalysis:
    """Analysis of a network route."""

    target: str
    target_ip: str
    hops: List[RouteHop]
    total_hops: int
    bottleneck_hop: Optional[RouteHop]
    avg_latency: float
    route_quality: str  # "excellent", "good", "fair", "poor"


async def traceroute(
    target: str, max_hops: int = 30, timeout: float = 3.0
) -> List[RouteHop]:
    """
    Perform traceroute to target using system command.
    Works cross-platform.
    """
    system = platform.system().lower()

    if system == "windows":
        cmd = f"tracert -d -h {max_hops} -w {int(timeout * 1000)} {target}"
    else:
        cmd = f"traceroute -n -m {max_hops} -w {timeout} {target}"

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(
            proc.communicate(), timeout=max_hops * timeout + 10
        )
        output = stdout.decode(errors="replace")
    except (asyncio.TimeoutError, OSError):
        return []

    return _parse_traceroute(output, system)


def _parse_traceroute(output: str, system: str) -> List[RouteHop]:
    """Parse traceroute output into structured hops."""
    hops: List[RouteHop] = []
    lines = output.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match hop number at start
        hop_match = re.match(r"^\s*(\d+)\s+", line)
        if not hop_match:
            continue

        hop_num = int(hop_match.group(1))

        # Check for timeout
        if "* * *" in line or "Request timed out" in line:
            hops.append(RouteHop(
                hop_number=hop_num, ip=None, hostname=None,
                latency_ms=-1, is_reachable=False
            ))
            continue

        # Extract IP addresses
        ip_pattern = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        ip_match = re.search(ip_pattern, line)
        ip = ip_match.group(1) if ip_match else None

        # Extract latency values
        latency_pattern = r"([\d.]+)\s*ms"
        latency_matches = re.findall(latency_pattern, line)
        latencies = [float(l) for l in latency_matches if float(l) > 0]

        avg_latency = statistics.mean(latencies) if latencies else -1

        hops.append(RouteHop(
            hop_number=hop_num,
            ip=ip,
            hostname=None,
            latency_ms=round(avg_latency, 2),
            is_reachable=ip is not None,
        ))

    return hops


async def analyze_route(
    target: str, config: OptimizationConfig
) -> RouteAnalysis:
    """
    Perform full route analysis including traceroute and bottleneck detection.
    """
    import socket

    try:
        target_ip = socket.gethostbyname(target)
    except socket.gaierror:
        target_ip = target

    hops = await traceroute(target, max_hops=config.max_hops)

    reachable_hops = [h for h in hops if h.is_reachable and h.latency_ms > 0]

    if not reachable_hops:
        return RouteAnalysis(
            target=target,
            target_ip=target_ip,
            hops=hops,
            total_hops=len(hops),
            bottleneck_hop=None,
            avg_latency=-1,
            route_quality="poor",
        )

    # Find bottleneck: hop with highest latency increase
    bottleneck = None
    max_increase = 0

    for i in range(1, len(reachable_hops)):
        increase = reachable_hops[i].latency_ms - reachable_hops[i - 1].latency_ms
        if increase > max_increase:
            max_increase = increase
            bottleneck = reachable_hops[i]

    avg_latency = statistics.mean([h.latency_ms for h in reachable_hops])

    # Determine route quality
    final_latency = reachable_hops[-1].latency_ms if reachable_hops else -1
    if final_latency < 30:
        quality = "excellent"
    elif final_latency < 60:
        quality = "good"
    elif final_latency < 100:
        quality = "fair"
    else:
        quality = "poor"

    result = RouteAnalysis(
        target=target,
        target_ip=target_ip,
        hops=hops,
        total_hops=len(hops),
        bottleneck_hop=bottleneck,
        avg_latency=round(avg_latency, 2),
        route_quality=quality,
    )

    # Record into route intelligence history
    try:
        from intelligence import RouteHistory
        q_map = {"excellent": 95, "good": 75, "fair": 50, "poor": 25}
        route_hist = RouteHistory()
        route_hist.record(
            target, len(hops), round(avg_latency, 2),
            q_map.get(quality, 25),
            bottleneck.ip if bottleneck and bottleneck.ip else None,
        )
        route_hist.save()
    except Exception:
        pass

    return result


async def compare_routes(
    targets: List[str], config: OptimizationConfig
) -> List[RouteAnalysis]:
    """Analyze routes to multiple targets and rank them."""
    tasks = [analyze_route(t, config) for t in targets]
    analyses = await asyncio.gather(*tasks)

    # Sort by route quality and latency
    quality_order = {"excellent": 0, "good": 1, "fair": 2, "poor": 3}
    return sorted(
        analyses,
        key=lambda a: (quality_order.get(a.route_quality, 4), a.avg_latency),
    )


async def find_optimal_mtu(
    target: str, start_mtu: int = 1500, min_mtu: int = 576
) -> int:
    """
    Find the optimal MTU by testing decreasing sizes.
    Avoids fragmentation which increases latency.
    """
    system = platform.system().lower()
    current_mtu = start_mtu

    while current_mtu >= min_mtu:
        if system == "windows":
            cmd = f"ping -n 1 -f -l {current_mtu - 28} {target}"
        elif system == "darwin":
            cmd = f"ping -c 1 -D -s {current_mtu - 28} {target}"
        else:
            cmd = f"ping -c 1 -M do -s {current_mtu - 28} {target}"

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=5
            )
            output = (stdout + stderr).decode(errors="replace").lower()

            if proc.returncode == 0 and "frag" not in output:
                return current_mtu
        except (asyncio.TimeoutError, OSError):
            pass

        current_mtu -= 10

    return min_mtu


async def multi_path_test(
    target: str, test_count: int = 5
) -> Tuple[float, float, float]:
    """
    Test multiple connection paths to find variance.
    Returns (best_ms, avg_ms, worst_ms).
    """
    latencies: List[float] = []

    for _ in range(test_count):
        lat = await tcp_ping(target, port=80, timeout=3.0)
        if lat > 0:
            latencies.append(lat)
        # Also test on 443
        lat443 = await tcp_ping(target, port=443, timeout=3.0)
        if lat443 > 0:
            latencies.append(lat443)
        await asyncio.sleep(0.2)

    if not latencies:
        return (-1, -1, -1)

    return (
        round(min(latencies), 2),
        round(statistics.mean(latencies), 2),
        round(max(latencies), 2),
    )
