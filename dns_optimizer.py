"""
UltimatePing - DNS Optimizer
Tests DNS servers and finds the fastest resolver for game server lookups.
"""

import asyncio
import socket
import struct
import time
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from config import DNS_SERVERS, OptimizationConfig


@dataclass
class DNSResult:
    """Result of DNS performance test."""

    name: str
    primary_ip: str
    secondary_ip: str
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    reliability: float  # percentage of successful queries
    resolved_correctly: bool


def _build_dns_query(domain: str) -> bytes:
    """Build a DNS query packet for A record lookup."""
    # Header
    transaction_id = struct.pack('!H', 0x1234)
    flags = struct.pack('!H', 0x0100)  # Standard query, recursion desired
    counts = struct.pack('!HHHH', 1, 0, 0, 0)  # 1 question

    # Question
    question = b''
    for part in domain.split('.'):
        question += bytes([len(part)]) + part.encode()
    question += b'\x00'
    question += struct.pack('!HH', 1, 1)  # Type A, Class IN

    return transaction_id + flags + counts + question


async def _dns_query(
    dns_ip: str, domain: str, timeout: float = 2.0
) -> Tuple[float, bool]:
    """
    Send DNS query via UDP and measure response time.
    Returns (latency_ms, success).
    """
    query = _build_dns_query(domain)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        sock.settimeout(timeout)

        loop = asyncio.get_event_loop()
        start = time.perf_counter()

        await loop.sock_sendto(sock, query, (dns_ip, 53))
        data = await asyncio.wait_for(
            loop.sock_recv(sock, 512), timeout=timeout
        )
        latency = (time.perf_counter() - start) * 1000

        # Check response has answers
        if len(data) > 12:
            answer_count = struct.unpack('!H', data[6:8])[0]
            return (latency, answer_count > 0)
        return (latency, False)

    except (asyncio.TimeoutError, OSError):
        return (-1, False)
    finally:
        try:
            sock.close()
        except Exception:
            pass


async def test_dns_server(
    name: str,
    dns_ip: str,
    secondary_ip: str,
    test_domains: List[str],
    count: int = 5,
    timeout: float = 2.0,
) -> DNSResult:
    """Test a DNS server's performance across multiple domains."""
    latencies: List[float] = []
    successes = 0
    total_tests = 0

    for domain in test_domains:
        for _ in range(count):
            total_tests += 1
            lat, ok = await _dns_query(dns_ip, domain, timeout)
            if ok and lat > 0:
                latencies.append(lat)
                successes += 1
            await asyncio.sleep(0.05)

    if not latencies:
        return DNSResult(
            name=name,
            primary_ip=dns_ip,
            secondary_ip=secondary_ip,
            avg_latency_ms=-1,
            min_latency_ms=-1,
            max_latency_ms=-1,
            reliability=0.0,
            resolved_correctly=False,
        )

    return DNSResult(
        name=name,
        primary_ip=dns_ip,
        secondary_ip=secondary_ip,
        avg_latency_ms=round(statistics.mean(latencies), 2),
        min_latency_ms=round(min(latencies), 2),
        max_latency_ms=round(max(latencies), 2),
        reliability=round((successes / total_tests) * 100, 1),
        resolved_correctly=True,
    )


async def benchmark_all_dns(
    config: OptimizationConfig,
    test_domains: Optional[List[str]] = None,
) -> List[DNSResult]:
    """
    Benchmark all known DNS servers and rank by performance.
    """
    if test_domains is None:
        test_domains = [
            "google.com",
            "cloudflare.com",
            "amazon.com",
            "riot.com",
            "epicgames.com",
        ]

    tasks = []
    for name, ips in DNS_SERVERS.items():
        primary = ips[0]
        secondary = ips[1] if len(ips) > 1 else ips[0]
        tasks.append(
            test_dns_server(
                name=name,
                dns_ip=primary,
                secondary_ip=secondary,
                test_domains=test_domains,
                count=config.dns_test_count,
                timeout=config.dns_timeout,
            )
        )

    results = await asyncio.gather(*tasks)

    # Record results into DNS intelligence history
    try:
        from intelligence import DNSHistory
        dns_hist = DNSHistory()
        for r in results:
            dns_hist.record(r.name, r.primary_ip,
                            r.avg_latency_ms if r.resolved_correctly else 999,
                            r.resolved_correctly)
        dns_hist.save()
    except Exception:
        pass

    # Sort by avg latency (failed ones last)
    # Blend with historical scores for smarter ranking
    try:
        from intelligence import DNSHistory as _DH
        _hist = _DH()
        for r in results:
            if r.resolved_correctly:
                h = _hist.get(r.primary_ip)
                if h and h.samples >= 3:
                    # Weight historical score into latency ranking
                    r._sort_key = r.avg_latency_ms * 0.6 + (100 - h.score) * 0.4
                else:
                    r._sort_key = r.avg_latency_ms
            else:
                r._sort_key = 99999
    except Exception:
        for r in results:
            r._sort_key = r.avg_latency_ms if r.resolved_correctly else 99999

    working = sorted(
        [r for r in results if r.resolved_correctly],
        key=lambda r: getattr(r, '_sort_key', r.avg_latency_ms),
    )
    failed = [r for r in results if not r.resolved_correctly]

    return working + failed


async def get_best_dns(
    config: OptimizationConfig,
) -> Optional[DNSResult]:
    """Find the single best DNS server."""
    results = await benchmark_all_dns(config)
    for r in results:
        if r.resolved_correctly and r.reliability > 80:
            return r
    return None


def get_current_dns() -> List[str]:
    """Get the current system DNS servers."""
    import platform

    system = platform.system().lower()
    dns_servers: List[str] = []

    if system == "darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["scutil", "--dns"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "nameserver" in line:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        ip = parts[-1]
                        # Validate IP format
                        try:
                            socket.inet_aton(ip)
                            if ip not in dns_servers:
                                dns_servers.append(ip)
                        except socket.error:
                            pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    elif system == "linux":
        try:
            with open("/etc/resolv.conf") as f:
                for line in f:
                    if line.strip().startswith("nameserver"):
                        ip = line.strip().split()[1]
                        if ip not in dns_servers:
                            dns_servers.append(ip)
        except FileNotFoundError:
            pass

    elif system == "windows":
        try:
            import subprocess
            result = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True, text=True, timeout=10
            )
            import re
            for match in re.finditer(
                r"DNS Servers.*?:\s*([\d.]+)", result.stdout
            ):
                ip = match.group(1)
                if ip not in dns_servers:
                    dns_servers.append(ip)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return dns_servers or ["8.8.8.8"]
