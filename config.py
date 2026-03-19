"""
UltimatePing - Configuration
Global settings and game server definitions.
"""

import platform
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json

# ─── Game Server Database ────────────────────────────────────────────────────

GAME_SERVERS: Dict[str, Dict[str, List[str]]] = {
    "valorant": {
        "NA": ["dynamodb.us-east-1.amazonaws.com", "dynamodb.us-west-2.amazonaws.com"],
        "EU": ["dynamodb.eu-west-1.amazonaws.com", "dynamodb.eu-central-1.amazonaws.com"],
        "ASIA": ["dynamodb.ap-southeast-1.amazonaws.com", "dynamodb.ap-northeast-1.amazonaws.com"],
        "SA": ["dynamodb.sa-east-1.amazonaws.com"],
        "OCE": ["dynamodb.ap-southeast-2.amazonaws.com"],
    },
    "league_of_legends": {
        "NA": ["104.160.131.3", "104.160.141.3"],
        "EU_WEST": ["104.160.141.3"],
        "EU_EAST": ["104.160.142.3"],
        "ASIA": ["104.160.136.3"],
        "OCE": ["104.160.156.1"],
    },
    "fortnite": {
        "NA_EAST": ["ping-nae.ds.on.epicgames.com"],
        "NA_WEST": ["ping-naw.ds.on.epicgames.com"],
        "EU": ["ping-eu.ds.on.epicgames.com"],
        "ASIA": ["ping-asia.ds.on.epicgames.com"],
        "OCE": ["ping-oce.ds.on.epicgames.com"],
    },
    "cs2": {
        "NA": ["162.254.199.170", "162.254.197.70"],
        "EU_WEST": ["162.254.196.83", "155.133.248.34"],
        "EU_EAST": ["162.254.192.100"],
        "ASIA": ["103.10.124.1"],
        "SA": ["205.185.194.10"],
        "OCE": ["103.10.124.200"],
    },
    "apex_legends": {
        "NA": ["dynamodb.us-east-1.amazonaws.com", "dynamodb.us-west-2.amazonaws.com"],
        "EU": ["dynamodb.eu-west-1.amazonaws.com", "dynamodb.eu-central-1.amazonaws.com"],
        "ASIA": ["dynamodb.ap-northeast-1.amazonaws.com", "dynamodb.ap-southeast-1.amazonaws.com"],
    },
    "overwatch2": {
        "NA": ["24.105.30.129"],
        "EU": ["185.60.112.157"],
        "ASIA": ["121.254.173.20"],
    },
    "dota2": {
        "NA": ["162.254.199.170"],
        "EU_WEST": ["162.254.196.83"],
        "EU_EAST": ["162.254.192.100"],
        "ASIA": ["103.10.124.1"],
        "SA": ["205.185.194.10"],
    },
    "pubg": {
        "NA": ["dynamodb.us-east-1.amazonaws.com", "dynamodb.us-west-2.amazonaws.com"],
        "EU": ["dynamodb.eu-west-1.amazonaws.com", "dynamodb.eu-central-1.amazonaws.com"],
        "ASIA": ["dynamodb.ap-northeast-2.amazonaws.com", "dynamodb.ap-southeast-1.amazonaws.com"],
        "SA": ["dynamodb.sa-east-1.amazonaws.com"],
        "OCE": ["dynamodb.ap-southeast-2.amazonaws.com"],
    },
    "custom": {},
}

# ─── DNS Servers ─────────────────────────────────────────────────────────────

DNS_SERVERS = {
    "Cloudflare": ["1.1.1.1", "1.0.0.1"],
    "Google": ["8.8.8.8", "8.8.4.4"],
    "OpenDNS": ["208.67.222.222", "208.67.220.220"],
    "Quad9": ["9.9.9.9", "149.112.112.112"],
    "CleanBrowsing": ["185.228.168.9", "185.228.169.9"],
    "AdGuard": ["94.140.14.14", "94.140.15.15"],
    "NextDNS": ["45.90.28.0", "45.90.30.0"],
    "Level3": ["209.244.0.3", "209.244.0.4"],
}

# ─── Configuration Dataclass ─────────────────────────────────────────────────


@dataclass
class OptimizationConfig:
    """Main configuration for network optimization."""

    # Ping settings
    ping_count: int = 10
    ping_timeout: float = 2.0
    ping_interval: float = 0.5

    # Monitor settings
    monitor_interval: float = 1.0
    monitor_history_size: int = 100

    # Route optimization
    max_hops: int = 30
    route_test_count: int = 5

    # TCP tuning
    tcp_recv_buffer: int = 4194304  # 4MB
    tcp_send_buffer: int = 4194304  # 4MB
    tcp_nodelay: bool = True
    tcp_quickack: bool = True

    # UDP tuning
    udp_recv_buffer: int = 4194304
    udp_send_buffer: int = 4194304

    # DNS settings
    dns_timeout: float = 2.0
    dns_test_count: int = 5

    # System
    os_type: str = field(default_factory=lambda: platform.system().lower())
    config_dir: Path = field(
        default_factory=lambda: Path.home() / ".ultimateping"
    )

    # Selected game
    selected_game: Optional[str] = None
    selected_region: Optional[str] = None
    custom_servers: List[str] = field(default_factory=list)

    def save(self) -> None:
        """Save configuration to disk."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        config_file = self.config_dir / "config.json"
        data = {
            "ping_count": self.ping_count,
            "ping_timeout": self.ping_timeout,
            "ping_interval": self.ping_interval,
            "monitor_interval": self.monitor_interval,
            "tcp_recv_buffer": self.tcp_recv_buffer,
            "tcp_send_buffer": self.tcp_send_buffer,
            "tcp_nodelay": self.tcp_nodelay,
            "udp_recv_buffer": self.udp_recv_buffer,
            "udp_send_buffer": self.udp_send_buffer,
            "selected_game": self.selected_game,
            "selected_region": self.selected_region,
            "custom_servers": self.custom_servers,
        }
        config_file.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls) -> "OptimizationConfig":
        """Load configuration from disk, or return defaults."""
        config = cls()
        config_file = config.config_dir / "config.json"
        if config_file.exists():
            data = json.loads(config_file.read_text())
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        return config
