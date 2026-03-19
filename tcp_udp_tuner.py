"""
UltimatePing - TCP/UDP Socket Tuner
Optimizes socket parameters for gaming traffic.
"""

import platform
import socket
from dataclasses import dataclass
from typing import Dict, List, Optional

from config import OptimizationConfig


@dataclass
class SocketProfile:
    """Optimized socket settings for a game type."""

    name: str
    tcp_nodelay: bool
    tcp_quickack: bool
    recv_buffer: int
    send_buffer: int
    keep_alive: bool
    keep_alive_interval: int
    description: str


# ─── Predefined Profiles ────────────────────────────────────────────────────

GAMING_PROFILES: Dict[str, SocketProfile] = {
    "competitive_fps": SocketProfile(
        name="Competitive FPS",
        tcp_nodelay=True,
        tcp_quickack=True,
        recv_buffer=262144,     # 256KB - smaller for speed
        send_buffer=262144,
        keep_alive=True,
        keep_alive_interval=15,
        description="Optimized for fast-paced FPS games. Minimizes send delay.",
    ),
    "moba": SocketProfile(
        name="MOBA/Strategy",
        tcp_nodelay=True,
        tcp_quickack=True,
        recv_buffer=524288,     # 512KB
        send_buffer=524288,
        keep_alive=True,
        keep_alive_interval=30,
        description="Balanced for MOBA games with frequent small packets.",
    ),
    "battle_royale": SocketProfile(
        name="Battle Royale",
        tcp_nodelay=True,
        tcp_quickack=True,
        recv_buffer=1048576,    # 1MB - larger for map data
        send_buffer=524288,
        keep_alive=True,
        keep_alive_interval=20,
        description="Handles larger world state updates in BR games.",
    ),
    "mmo": SocketProfile(
        name="MMO",
        tcp_nodelay=True,
        tcp_quickack=False,
        recv_buffer=2097152,    # 2MB
        send_buffer=1048576,
        keep_alive=True,
        keep_alive_interval=60,
        description="Larger buffers for MMO content streaming.",
    ),
    "ultra_low_latency": SocketProfile(
        name="Ultra Low Latency",
        tcp_nodelay=True,
        tcp_quickack=True,
        recv_buffer=131072,     # 128KB - minimal
        send_buffer=131072,
        keep_alive=True,
        keep_alive_interval=10,
        description="Absolute minimum latency. Small buffers, all optimizations on.",
    ),
}

# Map games to profiles
GAME_PROFILE_MAP = {
    "valorant": "competitive_fps",
    "cs2": "competitive_fps",
    "overwatch2": "competitive_fps",
    "apex_legends": "battle_royale",
    "fortnite": "battle_royale",
    "pubg": "battle_royale",
    "league_of_legends": "moba",
    "dota2": "moba",
}


def get_profile_for_game(game: str) -> SocketProfile:
    """Get the optimal socket profile for a game."""
    profile_key = GAME_PROFILE_MAP.get(game, "competitive_fps")
    return GAMING_PROFILES[profile_key]


def get_intelligent_profile(game: Optional[str] = None) -> SocketProfile:
    """
    Get an intelligently-adapted socket profile based on game AND network conditions.
    Falls back to standard profile if intelligence is unavailable.
    """
    try:
        from intelligence import assess_network, intelligent_socket_config
        import asyncio

        loop = asyncio.new_event_loop()
        cond = loop.run_until_complete(assess_network())
        loop.close()

        cfg, _ = intelligent_socket_config(cond, game)
        return SocketProfile(
            name=f"Intelligent ({cond.quality})",
            tcp_nodelay=cfg.tcp_nodelay,
            tcp_quickack=cfg.tcp_quickack,
            recv_buffer=cfg.recv_buffer,
            send_buffer=cfg.send_buffer,
            keep_alive=True,
            keep_alive_interval=cfg.keep_alive_interval,
            description=cfg.reason,
        )
    except Exception:
        return get_profile_for_game(game or "valorant")


def create_optimized_tcp_socket(
    profile: SocketProfile,
) -> socket.socket:
    """Create a TCP socket with optimized settings."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Disable Nagle's algorithm for immediate packet sending
    if profile.tcp_nodelay:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    # Quick ACK (Linux only)
    system = platform.system().lower()
    if profile.tcp_quickack and system == "linux":
        try:
            TCP_QUICKACK = 12  # Linux constant
            sock.setsockopt(socket.IPPROTO_TCP, TCP_QUICKACK, 1)
        except OSError:
            pass

    # Buffer sizes
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, profile.recv_buffer)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, profile.send_buffer)

    # Keep-alive
    if profile.keep_alive:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if system == "linux":
            sock.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_KEEPIDLE,
                profile.keep_alive_interval
            )
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
        elif system == "darwin":
            TCP_KEEPALIVE_MACOS = 0x10
            try:
                sock.setsockopt(
                    socket.IPPROTO_TCP, TCP_KEEPALIVE_MACOS,
                    profile.keep_alive_interval
                )
            except OSError:
                pass

    # Reuse address
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    return sock


def create_optimized_udp_socket(
    profile: SocketProfile,
) -> socket.socket:
    """Create a UDP socket with optimized settings."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Buffer sizes
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, profile.recv_buffer)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, profile.send_buffer)

    # Reuse address
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    return sock


def get_current_socket_settings() -> Dict[str, int]:
    """Read current system socket buffer defaults."""
    settings = {}
    system = platform.system().lower()

    if system == "linux":
        paths = {
            "tcp_rmem_default": "/proc/sys/net/ipv4/tcp_rmem",
            "tcp_wmem_default": "/proc/sys/net/ipv4/tcp_wmem",
            "udp_rmem": "/proc/sys/net/core/rmem_default",
            "udp_wmem": "/proc/sys/net/core/wmem_default",
            "tcp_nodelay": "/proc/sys/net/ipv4/tcp_low_latency",
        }
        for name, path in paths.items():
            try:
                with open(path) as f:
                    content = f.read().strip()
                    values = content.split()
                    settings[name] = int(values[-1]) if values else 0
            except (FileNotFoundError, ValueError):
                settings[name] = 0

    else:
        # Probe using actual socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            settings["tcp_rcvbuf"] = sock.getsockopt(
                socket.SOL_SOCKET, socket.SO_RCVBUF
            )
            settings["tcp_sndbuf"] = sock.getsockopt(
                socket.SOL_SOCKET, socket.SO_SNDBUF
            )
            settings["tcp_nodelay"] = sock.getsockopt(
                socket.IPPROTO_TCP, socket.TCP_NODELAY
            )
            sock.close()
        except OSError:
            pass

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            settings["udp_rcvbuf"] = sock.getsockopt(
                socket.SOL_SOCKET, socket.SO_RCVBUF
            )
            settings["udp_sndbuf"] = sock.getsockopt(
                socket.SOL_SOCKET, socket.SO_SNDBUF
            )
            sock.close()
        except OSError:
            pass

    return settings


def generate_optimization_report(
    profile: SocketProfile, current: Dict[str, int]
) -> List[str]:
    """Generate a report of what will be changed."""
    changes: List[str] = []

    if profile.tcp_nodelay:
        nodelay = current.get("tcp_nodelay", 0)
        if not nodelay:
            changes.append("✓ Enable TCP_NODELAY (disable Nagle's algorithm)")

    tcp_rcv = current.get("tcp_rcvbuf", current.get("tcp_rmem_default", 0))
    if tcp_rcv and tcp_rcv != profile.recv_buffer:
        changes.append(
            f"✓ TCP receive buffer: {tcp_rcv:,} → {profile.recv_buffer:,} bytes"
        )

    tcp_snd = current.get("tcp_sndbuf", current.get("tcp_wmem_default", 0))
    if tcp_snd and tcp_snd != profile.send_buffer:
        changes.append(
            f"✓ TCP send buffer: {tcp_snd:,} → {profile.send_buffer:,} bytes"
        )

    if profile.keep_alive:
        changes.append(
            f"✓ Enable TCP keep-alive (interval: {profile.keep_alive_interval}s)"
        )

    if not changes:
        changes.append("✓ Current settings are already optimal!")

    return changes
