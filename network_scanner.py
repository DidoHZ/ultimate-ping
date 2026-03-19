"""
UltimatePing - Network Scanner
Discovers network interfaces, tests connectivity, and measures baseline latency.
"""

import asyncio
import socket
import struct
import time
import statistics
from dataclasses import dataclass
from typing import List, Optional, Tuple

from config import OptimizationConfig


@dataclass
class PingResult:
    """Result of a single ping measurement."""

    host: str
    ip: str
    latency_ms: float
    is_reachable: bool
    ttl: int = 0
    packet_loss: float = 0.0


@dataclass
class NetworkInfo:
    """Information about network interface and connectivity."""

    interface: str
    local_ip: str
    gateway: Optional[str]
    dns_servers: List[str]
    mtu: int = 1500


def _checksum(data: bytes) -> int:
    """Calculate ICMP checksum."""
    if len(data) % 2:
        data += b'\x00'
    total = 0
    for i in range(0, len(data), 2):
        total += (data[i] << 8) + data[i + 1]
    total = (total >> 16) + (total & 0xFFFF)
    total += total >> 16
    return ~total & 0xFFFF


def _build_icmp_packet(identifier: int, sequence: int) -> bytes:
    """Build an ICMP echo request packet."""
    icmp_type = 8  # Echo request
    code = 0
    checksum_val = 0
    payload = b'UltimatePing' + struct.pack('d', time.time())

    header = struct.pack(
        '!BBHHH', icmp_type, code, checksum_val, identifier, sequence
    )
    checksum_val = _checksum(header + payload)
    header = struct.pack(
        '!BBHHH', icmp_type, code, checksum_val, identifier, sequence
    )
    return header + payload


async def tcp_ping(host: str, port: int = 80, timeout: float = 2.0) -> float:
    """
    Measure latency using TCP handshake (SYN → SYN-ACK).
    Works without root privileges.
    Returns latency in milliseconds, or -1 if unreachable.
    """
    try:
        start = time.perf_counter()
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        latency = (time.perf_counter() - start) * 1000
        writer.close()
        await writer.wait_closed()
        return latency
    except (asyncio.TimeoutError, OSError, ConnectionRefusedError):
        return -1.0


async def icmp_ping(
    host: str, timeout: float = 2.0, identifier: int = 1
) -> float:
    """
    Send ICMP echo request and measure round-trip time.
    Requires root/admin privileges.
    Returns latency in ms, or -1 if unreachable.
    """
    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror:
        return -1.0

    try:
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP
        )
    except PermissionError:
        # Fallback to TCP ping if no raw socket permission
        return await tcp_ping(host, timeout=timeout)

    sock.settimeout(timeout)
    sock.setblocking(False)

    loop = asyncio.get_event_loop()
    packet = _build_icmp_packet(identifier, 1)
    start = time.perf_counter()

    try:
        await loop.sock_sendto(sock, packet, (ip, 0))
        data = await asyncio.wait_for(
            loop.sock_recv(sock, 1024), timeout=timeout
        )
        latency = (time.perf_counter() - start) * 1000

        # Parse ICMP response
        icmp_header = data[20:28]
        icmp_type, _, _, recv_id, _ = struct.unpack('!BBHHH', icmp_header)
        if icmp_type == 0 and recv_id == identifier:
            return latency
        return -1.0
    except (asyncio.TimeoutError, OSError):
        return -1.0
    finally:
        sock.close()


async def multi_ping(
    host: str,
    count: int = 10,
    interval: float = 0.5,
    timeout: float = 2.0,
    use_tcp: bool = False,
    tcp_port: int = 80,
) -> PingResult:
    """
    Send multiple pings and compute statistics.
    Falls back to TCP ping if ICMP is not available.
    """
    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror:
        return PingResult(
            host=host, ip="unresolved", latency_ms=-1,
            is_reachable=False, packet_loss=100.0
        )

    latencies: List[float] = []
    lost = 0

    for i in range(count):
        if use_tcp:
            lat = await tcp_ping(host, port=tcp_port, timeout=timeout)
        else:
            lat = await icmp_ping(host, timeout=timeout, identifier=i + 1)
        if lat < 0:
            lost += 1
        else:
            latencies.append(lat)
        if i < count - 1:
            await asyncio.sleep(interval)

    packet_loss = (lost / count) * 100.0

    if latencies:
        avg_latency = statistics.mean(latencies)
        return PingResult(
            host=host, ip=ip, latency_ms=round(avg_latency, 2),
            is_reachable=True, packet_loss=round(packet_loss, 1)
        )
    else:
        return PingResult(
            host=host, ip=ip, latency_ms=-1,
            is_reachable=False, packet_loss=100.0
        )


async def scan_servers(
    servers: List[str],
    config: OptimizationConfig,
    use_tcp: bool = False,
) -> List[PingResult]:
    """Ping multiple servers concurrently and return sorted results."""
    tasks = [
        multi_ping(
            host=server,
            count=config.ping_count,
            interval=config.ping_interval,
            timeout=config.ping_timeout,
            use_tcp=use_tcp,
        )
        for server in servers
    ]
    results = await asyncio.gather(*tasks)

    # Record all results into performance history
    try:
        from intelligence import PerformanceHistory
        hist = PerformanceHistory()
        for r in results:
            if r.is_reachable:
                hist.record(r.host, r.latency_ms, r.packet_loss)
        hist.save()
    except Exception:
        pass

    # Sort by latency (unreachable last)
    reachable = sorted(
        [r for r in results if r.is_reachable], key=lambda r: r.latency_ms
    )
    unreachable = [r for r in results if not r.is_reachable]
    return reachable + unreachable


def get_network_info() -> NetworkInfo:
    """Gather information about the current network configuration."""
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        local_ip = "127.0.0.1"

    # Detect gateway by connecting to external host
    gateway = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except OSError:
        pass

    return NetworkInfo(
        interface="auto",
        local_ip=local_ip,
        gateway=gateway,
        dns_servers=["8.8.8.8"],
    )


async def find_best_server(
    servers: List[str], config: OptimizationConfig
) -> Optional[PingResult]:
    """Find the server with the lowest latency."""
    results = await scan_servers(servers, config, use_tcp=True)
    return results[0] if results and results[0].is_reachable else None


async def measure_jitter(
    host: str, count: int = 20, interval: float = 0.3
) -> Tuple[float, float, float, float]:
    """
    Measure jitter (latency variance) to a host.
    Returns: (avg_ms, min_ms, max_ms, jitter_ms)
    """
    latencies: List[float] = []
    for _ in range(count):
        lat = await tcp_ping(host, timeout=2.0)
        if lat > 0:
            latencies.append(lat)
        await asyncio.sleep(interval)

    if len(latencies) < 2:
        return (-1, -1, -1, -1)

    avg = statistics.mean(latencies)
    min_lat = min(latencies)
    max_lat = max(latencies)

    # Jitter = average difference between consecutive pings
    diffs = [abs(latencies[i] - latencies[i - 1]) for i in range(1, len(latencies))]
    jitter = statistics.mean(diffs)

    return (round(avg, 2), round(min_lat, 2), round(max_lat, 2), round(jitter, 2))
