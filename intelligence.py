"""
UltimatePing — Intelligence Engine
Auto-detection, learning, adaptive strategies, and smart recommendations.
Covers ALL subsystems: server, DNS, route, TCP/UDP, OS, and monitoring.
"""

import asyncio
import json
import platform
import re
import socket
import subprocess
import time
import statistics as st
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import GAME_SERVERS, DNS_SERVERS, OptimizationConfig
from network_scanner import tcp_ping


# ─── Data Structures ─────────────────────────────────────────────────────────

@dataclass
class ServerRecord:
    """Historical performance data for a single server."""

    host: str
    samples: int = 0
    avg_ms: float = 0.0
    best_ms: float = float("inf")
    worst_ms: float = 0.0
    loss_pct: float = 0.0
    last_seen: float = 0.0
    score: float = 0.0          # 0-100 composite quality score

    def to_dict(self) -> dict:
        return {
            "host": self.host, "samples": self.samples,
            "avg_ms": self.avg_ms, "best_ms": self.best_ms,
            "worst_ms": self.worst_ms, "loss_pct": self.loss_pct,
            "last_seen": self.last_seen, "score": self.score,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ServerRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class GeoLocation:
    """Inferred user location."""

    country: str = ""
    region_code: str = ""       # mapped to our region keys (NA, EU, ASIA …)
    timezone: str = ""
    confidence: float = 0.0     # 0-1


@dataclass
class DetectedGame:
    """A running game process."""

    name: str                   # game key (e.g. "valorant")
    display_name: str
    pid: int
    process_name: str


@dataclass
class NetworkCondition:
    """Current network health snapshot."""

    base_latency_ms: float = 0.0
    jitter_ms: float = 0.0
    loss_pct: float = 0.0
    quality: str = "unknown"    # excellent / good / fair / poor / bad


@dataclass
class SmartRecommendation:
    """An actionable recommendation from the engine."""

    category: str       # server | dns | route | system | socket
    priority: int       # 1 (critical) … 5 (nice-to-have)
    title: str
    detail: str
    action_id: str      # machine-readable ID for the GUI to act on


# ─── DNS Intelligence Structures ─────────────────────────────────────────────

@dataclass
class DNSRecord:
    """Historical DNS performance data."""

    provider: str
    ip: str
    samples: int = 0
    avg_ms: float = 0.0
    best_ms: float = float("inf")
    worst_ms: float = 0.0
    reliability: float = 100.0
    last_seen: float = 0.0
    score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "provider": self.provider, "ip": self.ip,
            "samples": self.samples, "avg_ms": self.avg_ms,
            "best_ms": self.best_ms, "worst_ms": self.worst_ms,
            "reliability": self.reliability,
            "last_seen": self.last_seen, "score": self.score,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DNSRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RouteRecord:
    """Historical route performance data."""

    target: str
    samples: int = 0
    avg_hops: float = 0.0
    avg_latency_ms: float = 0.0
    best_latency_ms: float = float("inf")
    worst_latency_ms: float = 0.0
    avg_quality_score: float = 0.0  # 0-100
    last_seen: float = 0.0
    bottleneck_ips: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "target": self.target, "samples": self.samples,
            "avg_hops": self.avg_hops, "avg_latency_ms": self.avg_latency_ms,
            "best_latency_ms": self.best_latency_ms,
            "worst_latency_ms": self.worst_latency_ms,
            "avg_quality_score": self.avg_quality_score,
            "last_seen": self.last_seen,
            "bottleneck_ips": self.bottleneck_ips[:5],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RouteRecord":
        safe = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**safe)


@dataclass
class MonitorAnomaly:
    """Detected monitoring anomaly."""

    timestamp: float
    anomaly_type: str       # spike | dropout | jitter_burst | degradation
    severity: str           # low | medium | high | critical
    detail: str
    value: float = 0.0


@dataclass
class AdaptiveSocketConfig:
    """Intelligently-tuned socket parameters."""

    tcp_nodelay: bool = True
    tcp_quickack: bool = True
    recv_buffer: int = 262144
    send_buffer: int = 262144
    keep_alive_interval: int = 15
    reason: str = ""


@dataclass
class AdaptiveOSConfig:
    """Intelligently-selected OS optimizations."""

    recommended_indices: List[int] = field(default_factory=list)
    skip_indices: List[int] = field(default_factory=list)
    reason: str = ""


# ─── Process → Game mapping ──────────────────────────────────────────────────

_PROCESS_MAP: Dict[str, Tuple[str, str]] = {
    # process-name-lower → (game_key, display_name)
    "valorant":          ("valorant",          "Valorant"),
    "valorant-win64-shipping": ("valorant",    "Valorant"),
    "riotclientservices": ("valorant",         "Valorant"),
    "leagueclient":      ("league_of_legends", "League of Legends"),
    "league of legends":  ("league_of_legends", "League of Legends"),
    "leagueclientux":    ("league_of_legends", "League of Legends"),
    "fortniteclient-win64-shipping": ("fortnite", "Fortnite"),
    "fortnitelauncher":  ("fortnite",          "Fortnite"),
    "cs2":               ("cs2",               "Counter-Strike 2"),
    "csgo":              ("cs2",               "Counter-Strike 2"),
    "r5apex":            ("apex_legends",      "Apex Legends"),
    "overwatch":         ("overwatch2",        "Overwatch 2"),
    "dota2":             ("dota2",             "DOTA 2"),
    "tslgame":           ("pubg",              "PUBG"),
    "pubg":              ("pubg",              "PUBG"),
}

# Timezone → region heuristic  (matches substrings in IANA tz names)
_TZ_REGION: Dict[str, str] = {
    "America": "NA", "US": "NA", "Canada": "NA",
    "Europe": "EU", "Africa": "EU",
    "Asia": "ASIA", "Australia": "OCE", "Pacific": "OCE",
    "Brazil": "SA", "Chile": "SA", "Argentina": "SA",
}

# Common timezone *abbreviations* → region  (fallback when IANA name is unavailable)
_TZ_ABBREV_REGION: Dict[str, str] = {
    "CET": "EU", "CEST": "EU", "EET": "EU", "EEST": "EU",
    "WET": "EU", "WEST": "EU", "GMT": "EU", "BST": "EU",
    "MET": "EU", "MEZ": "EU", "MESZ": "EU", "IST": "EU",
    "MSK": "EU", "WAT": "EU", "CAT": "EU",
    "EST": "NA", "EDT": "NA", "CST": "NA", "CDT": "NA",
    "MST": "NA", "MDT": "NA", "PST": "NA", "PDT": "NA",
    "AKST": "NA", "AKDT": "NA", "HST": "NA",
    "JST": "ASIA", "KST": "ASIA", "CST_ASIA": "ASIA",
    "SGT": "ASIA", "HKT": "ASIA", "ICT": "ASIA",
    "WIB": "ASIA", "WITA": "ASIA", "WIT": "ASIA",
    "IST_ASIA": "ASIA", "PKT": "ASIA", "PHT": "ASIA",
    "AEST": "OCE", "AEDT": "OCE", "ACST": "OCE", "AWST": "OCE",
    "NZST": "OCE", "NZDT": "OCE",
    "BRT": "SA", "BRST": "SA", "ART": "SA", "CLT": "SA",
}

# ─── Disk persistence paths ─────────────────────────────────────────────────

def _data_dir() -> Path:
    d = Path.home() / ".ultimateping" / "intelligence"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _history_path() -> Path:
    return _data_dir() / "server_history.json"


def _geo_path() -> Path:
    return _data_dir() / "geo_cache.json"


def _netcond_path() -> Path:
    return _data_dir() / "network_baseline.json"


def _dns_history_path() -> Path:
    return _data_dir() / "dns_history.json"


def _route_history_path() -> Path:
    return _data_dir() / "route_history.json"


def _monitor_anomaly_path() -> Path:
    return _data_dir() / "monitor_anomalies.json"


# ═════════════════════════════════════════════════════════════════════════════
#  1.  GEO / REGION DETECTION
# ═════════════════════════════════════════════════════════════════════════════

def detect_region() -> GeoLocation:
    """
    Infer user's region from timezone and locale — no external API calls.
    Falls back to latency-based detection.
    """
    # try loading cached result (< 24 h old)
    cached = _load_geo_cache()
    if cached and cached.confidence > 0:
        return cached

    geo = GeoLocation()

    # ── method 1: timezone ──
    try:
        tz = time.tzname[0] if time.tzname else ""
        geo.timezone = tz

        import locale
        loc = locale.getdefaultlocale()[0] or ""  # e.g. "en_US"

        # Extract from IANA tz via /etc/localtime or dateutil
        tz_full = _iana_timezone()
        if tz_full:
            geo.timezone = tz_full
            for prefix, region in _TZ_REGION.items():
                if prefix.lower() in tz_full.lower():
                    geo.region_code = region
                    geo.confidence = 0.7
                    break

        # fallback: match timezone abbreviation (CET, EST, etc.)
        if not geo.region_code and tz:
            abbrev_region = _TZ_ABBREV_REGION.get(tz.upper())
            if abbrev_region:
                geo.region_code = abbrev_region
                geo.confidence = 0.65

        # fallback: locale country code
        if not geo.region_code and len(loc) >= 5:
            cc = loc[3:5].upper()
            geo.country = cc
            geo.region_code = _country_to_region(cc)
            if geo.region_code:
                geo.confidence = max(geo.confidence, 0.6)

    except Exception:
        pass

    if not geo.region_code:
        geo.region_code = "NA"
        geo.confidence = 0.2

    _save_geo_cache(geo)
    return geo


def _iana_timezone() -> str:
    """Try to read IANA timezone string."""
    system = platform.system().lower()
    if system == "darwin":
        # method 1: systemsetup (may need admin)
        try:
            r = subprocess.run(
                ["systemsetup", "-gettimezone"],
                capture_output=True, text=True, timeout=3,
            )
            # "Time Zone: America/New_York"
            parts = r.stdout.strip().split(": ", 1)
            if len(parts) == 2 and "/" in parts[1]:
                return parts[1]
        except Exception:
            pass
        # method 2: /etc/localtime symlink (works without admin)
        link = Path("/etc/localtime")
        if link.is_symlink():
            target = str(link.resolve())
            idx = target.find("zoneinfo/")
            if idx >= 0:
                return target[idx + 9:]
    elif system == "linux":
        tz_file = Path("/etc/timezone")
        if tz_file.exists():
            return tz_file.read_text().strip()
        link = Path("/etc/localtime")
        if link.is_symlink():
            target = str(link.resolve())
            # /usr/share/zoneinfo/America/New_York → America/New_York
            idx = target.find("zoneinfo/")
            if idx >= 0:
                return target[idx + 9:]
    elif system == "windows":
        try:
            r = subprocess.run(
                ["tzutil", "/g"],
                capture_output=True, text=True, timeout=3,
            )
            return r.stdout.strip()
        except Exception:
            pass
    return ""


def _country_to_region(cc: str) -> str:
    _map = {
        "US": "NA", "CA": "NA", "MX": "NA",
        "GB": "EU", "DE": "EU", "FR": "EU", "IT": "EU", "ES": "EU",
        "NL": "EU", "PL": "EU", "SE": "EU", "NO": "EU", "DK": "EU",
        "FI": "EU", "IE": "EU", "PT": "EU", "AT": "EU", "CH": "EU",
        "BE": "EU", "CZ": "EU", "GR": "EU", "HU": "EU", "RO": "EU",
        "BG": "EU", "HR": "EU", "SK": "EU", "SI": "EU", "LT": "EU",
        "LV": "EU", "EE": "EU", "RS": "EU", "UA": "EU",
        "RU": "EU", "TR": "EU",
        # North Africa / Middle East → EU (closest gaming servers)
        "DZ": "EU", "MA": "EU", "TN": "EU", "LY": "EU", "EG": "EU",
        "SA": "EU", "AE": "EU", "QA": "EU", "KW": "EU", "BH": "EU",
        "OM": "EU", "JO": "EU", "LB": "EU", "IQ": "EU", "IL": "EU",
        # South America
        "BR": "SA", "AR": "SA", "CL": "SA", "CO": "SA", "PE": "SA",
        "VE": "SA", "EC": "SA", "UY": "SA", "PY": "SA", "BO": "SA",
        # Asia
        "JP": "ASIA", "KR": "ASIA", "CN": "ASIA", "TW": "ASIA",
        "SG": "ASIA", "IN": "ASIA", "TH": "ASIA", "PH": "ASIA",
        "ID": "ASIA", "MY": "ASIA", "VN": "ASIA",
        # Oceania
        "AU": "OCE", "NZ": "OCE",
    }
    return _map.get(cc, "")


def _load_geo_cache() -> Optional[GeoLocation]:
    p = _geo_path()
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
        age_h = (time.time() - d.get("ts", 0)) / 3600
        if age_h > 24:
            return None
        return GeoLocation(
            country=d.get("country", ""),
            region_code=d.get("region_code", ""),
            timezone=d.get("timezone", ""),
            confidence=d.get("confidence", 0),
        )
    except Exception:
        return None


def _save_geo_cache(geo: GeoLocation):
    try:
        _geo_path().write_text(json.dumps({
            "country": geo.country, "region_code": geo.region_code,
            "timezone": geo.timezone, "confidence": geo.confidence,
            "ts": time.time(),
        }))
    except Exception:
        pass


async def detect_region_by_latency() -> str:
    """
    Determine closest region by pinging one representative host per region.
    Expensive but accurate — called when timezone detection is low-confidence.
    """
    probes = {
        "NA":   ("dynamodb.us-east-1.amazonaws.com", 443),
        "EU":   ("dynamodb.eu-west-1.amazonaws.com", 443),
        "ASIA": ("dynamodb.ap-northeast-1.amazonaws.com", 443),
        "SA":   ("dynamodb.sa-east-1.amazonaws.com", 443),
        "OCE":  ("dynamodb.ap-southeast-2.amazonaws.com", 443),
    }
    best_region, best_ms = "NA", 9999.0

    async def _probe(region: str, host: str, port: int):
        nonlocal best_region, best_ms
        lats = []
        for _ in range(3):
            ms = await tcp_ping(host, port, timeout=3.0)
            if ms > 0:
                lats.append(ms)
            await asyncio.sleep(0.05)
        if lats:
            avg = sum(lats) / len(lats)
            if avg < best_ms:
                best_ms = avg
                best_region = region

    await asyncio.gather(*[
        _probe(r, h, p) for r, (h, p) in probes.items()
    ])

    # update cache
    geo = detect_region()
    geo.region_code = best_region
    geo.confidence = 0.95
    _save_geo_cache(geo)

    return best_region


# ═════════════════════════════════════════════════════════════════════════════
#  2.  GAME PROCESS DETECTION
# ═════════════════════════════════════════════════════════════════════════════

def detect_running_games() -> List[DetectedGame]:
    """Scan running processes for known game executables."""
    system = platform.system().lower()
    found: List[DetectedGame] = []
    seen_keys: set = set()

    try:
        if system == "windows":
            raw = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5,
            ).stdout
            for line in raw.strip().splitlines():
                parts = line.strip().strip('"').split('","')
                if len(parts) >= 2:
                    proc = parts[0].lower().replace(".exe", "")
                    pid = int(parts[1]) if parts[1].isdigit() else 0
                    if proc in _PROCESS_MAP:
                        key, display = _PROCESS_MAP[proc]
                        if key not in seen_keys:
                            found.append(DetectedGame(key, display, pid, proc))
                            seen_keys.add(key)
        else:
            # macOS / Linux
            raw = subprocess.run(
                ["ps", "-eo", "pid,comm"],
                capture_output=True, text=True, timeout=5,
            ).stdout
            for line in raw.strip().splitlines()[1:]:
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    pid_str, proc = parts
                    proc_lower = proc.lower().strip().split("/")[-1]
                    for pattern, (key, display) in _PROCESS_MAP.items():
                        if pattern in proc_lower and key not in seen_keys:
                            pid = int(pid_str) if pid_str.isdigit() else 0
                            found.append(DetectedGame(key, display, pid, proc))
                            seen_keys.add(key)
                            break
    except Exception:
        pass

    return found


# ═════════════════════════════════════════════════════════════════════════════
#  3.  NETWORK CONDITION ASSESSMENT
# ═════════════════════════════════════════════════════════════════════════════

async def assess_network() -> NetworkCondition:
    """Quick 5-probe test to characterise current connection health."""
    targets = [
        ("1.1.1.1", 80),
        ("8.8.8.8", 53),
    ]
    all_lats: List[float] = []

    for host, port in targets:
        for _ in range(5):
            ms = await tcp_ping(host, port, timeout=2.0)
            if ms > 0:
                all_lats.append(ms)
            await asyncio.sleep(0.05)

    total_probes = len(targets) * 5
    loss = ((total_probes - len(all_lats)) / total_probes) * 100 if total_probes else 100

    if len(all_lats) < 2:
        return NetworkCondition(quality="bad", loss_pct=loss)

    avg = st.mean(all_lats)
    diffs = [abs(all_lats[i] - all_lats[i - 1]) for i in range(1, len(all_lats))]
    jitter = st.mean(diffs) if diffs else 0

    if avg < 20 and jitter < 5 and loss < 2:
        q = "excellent"
    elif avg < 50 and jitter < 15 and loss < 5:
        q = "good"
    elif avg < 100 and jitter < 30 and loss < 10:
        q = "fair"
    elif avg < 200:
        q = "poor"
    else:
        q = "bad"

    cond = NetworkCondition(
        base_latency_ms=round(avg, 1),
        jitter_ms=round(jitter, 1),
        loss_pct=round(loss, 1),
        quality=q,
    )
    # persist baseline
    try:
        _netcond_path().write_text(json.dumps({
            "base_latency_ms": cond.base_latency_ms,
            "jitter_ms": cond.jitter_ms,
            "loss_pct": cond.loss_pct,
            "quality": cond.quality,
            "ts": time.time(),
        }))
    except Exception:
        pass
    return cond


# ═════════════════════════════════════════════════════════════════════════════
#  4.  SERVER PERFORMANCE HISTORY (LEARNING)
# ═════════════════════════════════════════════════════════════════════════════

class PerformanceHistory:
    """Persistent store with exponential-weighted moving average per server."""

    _ALPHA = 0.3   # weight of new sample vs history

    def __init__(self):
        self._records: Dict[str, ServerRecord] = {}
        self._load()

    # ── persistence ──

    def _load(self):
        p = _history_path()
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text())
            for d in data:
                rec = ServerRecord.from_dict(d)
                self._records[rec.host] = rec
        except Exception:
            pass

    def save(self):
        try:
            out = [r.to_dict() for r in self._records.values()]
            _history_path().write_text(json.dumps(out, indent=1))
        except Exception:
            pass

    # ── update ──

    def record(self, host: str, latency_ms: float, loss_pct: float = 0.0):
        """Add one measurement, EWMA-blend into running stats."""
        rec = self._records.get(host)
        if not rec:
            rec = ServerRecord(host=host)
            self._records[host] = rec

        a = self._ALPHA
        if rec.samples == 0:
            rec.avg_ms = latency_ms
            rec.loss_pct = loss_pct
        else:
            rec.avg_ms = round(rec.avg_ms * (1 - a) + latency_ms * a, 2)
            rec.loss_pct = round(rec.loss_pct * (1 - a) + loss_pct * a, 2)

        rec.samples += 1
        rec.best_ms = min(rec.best_ms, latency_ms)
        rec.worst_ms = max(rec.worst_ms, latency_ms)
        rec.last_seen = time.time()
        rec.score = self._compute_score(rec)

    def _compute_score(self, r: ServerRecord) -> float:
        """0-100 score; higher is better."""
        s = 100.0
        # penalise latency
        if r.avg_ms > 20:
            s -= min(40, (r.avg_ms - 20) * 0.5)
        # penalise loss
        s -= r.loss_pct * 5
        # penalise instability (wide range)
        spread = r.worst_ms - r.best_ms
        if spread > 30:
            s -= min(20, spread * 0.2)
        # freshness bonus: recent data is more trustworthy
        age_h = (time.time() - r.last_seen) / 3600 if r.last_seen else 999
        if age_h > 6:
            s -= min(10, age_h * 0.3)
        return round(max(0, min(100, s)), 1)

    # ── query ──

    def get(self, host: str) -> Optional[ServerRecord]:
        return self._records.get(host)

    def ranked(self, hosts: List[str]) -> List[ServerRecord]:
        """Return subset of *hosts* sorted best score → worst, unknown last."""
        known = [self._records[h] for h in hosts if h in self._records]
        unknown = [ServerRecord(host=h) for h in hosts if h not in self._records]
        known.sort(key=lambda r: r.score, reverse=True)
        return known + unknown

    def best_for_game(self, game: str) -> Optional[ServerRecord]:
        """Best historically-performing server across all regions for *game*."""
        all_hosts = []
        for region_servers in GAME_SERVERS.get(game, {}).values():
            all_hosts.extend(region_servers)
        ranked = self.ranked(all_hosts)
        return ranked[0] if ranked and ranked[0].samples > 0 else None

    def prune(self, max_age_days: int = 30):
        """Remove records older than *max_age_days*."""
        cutoff = time.time() - (max_age_days * 86400)
        self._records = {
            h: r for h, r in self._records.items() if r.last_seen > cutoff
        }


# ═════════════════════════════════════════════════════════════════════════════
#  5.  ADAPTIVE PING STRATEGY
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class PingStrategy:
    """Dynamically computed ping parameters."""

    count: int = 10
    interval: float = 0.5
    timeout: float = 2.0
    use_tcp: bool = True
    tcp_port: int = 443
    reason: str = ""


def choose_ping_strategy(
    condition: NetworkCondition,
    game: Optional[str] = None,
) -> PingStrategy:
    """
    Adapt ping parameters to current network health and game type.
    Bad network → longer timeout, fewer probes to avoid queue collapse.
    Good network → more probes for tighter statistics.
    """
    ps = PingStrategy()

    q = condition.quality

    if q == "excellent":
        ps.count = 15
        ps.interval = 0.3
        ps.timeout = 1.5
        ps.reason = "Network excellent — tight probes for precision"
    elif q == "good":
        ps.count = 10
        ps.interval = 0.4
        ps.timeout = 2.0
        ps.reason = "Network good — balanced strategy"
    elif q == "fair":
        ps.count = 8
        ps.interval = 0.6
        ps.timeout = 3.0
        ps.reason = "Network fair — wider spacing, longer timeout"
    elif q in ("poor", "bad"):
        ps.count = 5
        ps.interval = 1.0
        ps.timeout = 5.0
        ps.reason = "Network degraded — conservative probes"

    # game-specific tweaks
    if game in ("valorant", "cs2", "overwatch2"):
        ps.tcp_port = 443
    elif game in ("fortnite", "apex_legends", "pubg"):
        ps.tcp_port = 443
    elif game in ("league_of_legends", "dota2"):
        ps.tcp_port = 80

    return ps


# ═════════════════════════════════════════════════════════════════════════════
#  6.  SMART RECOMMENDATIONS
# ═════════════════════════════════════════════════════════════════════════════

async def generate_recommendations(
    game: Optional[str] = None,
    region: Optional[str] = None,
) -> List[SmartRecommendation]:
    """
    Analyse current state and history to produce prioritised recommendations.
    """
    recs: List[SmartRecommendation] = []
    hist = PerformanceHistory()
    cond = await assess_network()

    # ── network quality warnings ──
    if cond.quality in ("poor", "bad"):
        recs.append(SmartRecommendation(
            category="system", priority=1,
            title="Network quality is degraded",
            detail=(
                f"Base latency {cond.base_latency_ms}ms, jitter {cond.jitter_ms}ms, "
                f"loss {cond.loss_pct}%. Try applying system optimizations."
            ),
            action_id="apply_os_tweaks",
        ))

    if cond.jitter_ms > 15:
        recs.append(SmartRecommendation(
            category="system", priority=2,
            title="High jitter detected",
            detail=(
                f"Jitter {cond.jitter_ms}ms — consider disabling Wi-Fi power save "
                "and enabling TCP Fast Open."
            ),
            action_id="apply_os_tweaks",
        ))

    if cond.loss_pct > 5:
        recs.append(SmartRecommendation(
            category="system", priority=1,
            title="Significant packet loss",
            detail=f"{cond.loss_pct}% loss — check your connection or switch to ethernet.",
            action_id="diagnose_network",
        ))

    # ── region suggestion ──
    if not region:
        geo = detect_region()
        if geo.confidence < 0.6:
            recs.append(SmartRecommendation(
                category="server", priority=3,
                title="Region detection uncertain",
                detail="Run a latency-based region test for best accuracy.",
                action_id="detect_region_latency",
            ))
        else:
            recs.append(SmartRecommendation(
                category="server", priority=4,
                title=f"Auto-detected region: {geo.region_code}",
                detail=f"Based on timezone {geo.timezone} (confidence {geo.confidence:.0%}).",
                action_id="set_region",
            ))

    # ── game-specific ──
    if game:
        best = hist.best_for_game(game)
        if best and best.samples >= 3:
            recs.append(SmartRecommendation(
                category="server", priority=2,
                title=f"Recommended server: {best.host}",
                detail=(
                    f"Historically best at {best.avg_ms}ms avg, "
                    f"score {best.score}/100 ({best.samples} sessions)."
                ),
                action_id=f"use_server:{best.host}",
            ))

    # ── DNS ──
    from dns_optimizer import get_current_dns
    dns = get_current_dns()
    if dns and dns[0] not in ("1.1.1.1", "8.8.8.8", "9.9.9.9"):
        recs.append(SmartRecommendation(
            category="dns", priority=3,
            title="Non-optimal DNS detected",
            detail=f"Current: {dns[0]} — run DNS benchmark for a faster resolver.",
            action_id="benchmark_dns",
        ))

    recs.sort(key=lambda r: r.priority)
    return recs


# ═════════════════════════════════════════════════════════════════════════════
#  7.  INTELLIGENT SERVER SELECTOR  (orchestrates everything)
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class IntelligentResult:
    """Output of the smart server selection pipeline."""

    best_server: Optional[str] = None
    best_latency: float = -1
    region_used: str = ""
    ping_strategy: Optional[PingStrategy] = None
    network_condition: Optional[NetworkCondition] = None
    recommendations: List[SmartRecommendation] = field(default_factory=list)
    running_game: Optional[DetectedGame] = None
    history_informed: bool = False


async def smart_select(
    game: Optional[str] = None,
    region: Optional[str] = None,
) -> IntelligentResult:
    """
    Full intelligent pipeline:
      1. Detect running game (if not specified)
      2. Detect region (if not specified)
      3. Assess network condition
      4. Choose adaptive ping strategy
      5. Test servers  (history + live probes, merged scoring)
      6. Record results into history
      7. Generate recommendations
    """
    result = IntelligentResult()
    hist = PerformanceHistory()

    # 1 — detect game
    if not game:
        detected = detect_running_games()
        if detected:
            game = detected[0].name
            result.running_game = detected[0]

    # 2 — detect region
    if not region:
        geo = detect_region()
        if geo.confidence < 0.5:
            region = await detect_region_by_latency()
        else:
            region = geo.region_code
    result.region_used = region or "NA"

    # 3 — network condition
    cond = await assess_network()
    result.network_condition = cond

    # 4 — adaptive strategy
    strategy = choose_ping_strategy(cond, game)
    result.ping_strategy = strategy

    # 5 — select & test servers
    servers: List[str] = []
    if game and game in GAME_SERVERS:
        game_data = GAME_SERVERS[game]
        # prefer detected region, but include others as fallbacks
        if region and region in game_data:
            servers.extend(game_data[region])
        # add all remaining regions
        for r, svs in game_data.items():
            for s in svs:
                if s not in servers:
                    servers.append(s)
    else:
        # test representative hosts
        servers = [
            "dynamodb.us-east-1.amazonaws.com",
            "dynamodb.eu-west-1.amazonaws.com",
            "dynamodb.ap-northeast-1.amazonaws.com",
        ]

    if not servers:
        return result

    # prefer servers with strong history
    ranked = hist.ranked(servers)
    # put servers with best history first for optimistic short-circuit
    ordered = [r.host for r in ranked]

    best_host = None
    best_ms = 9999.0

    for host in ordered:
        lats = []
        for _ in range(strategy.count):
            ms = await tcp_ping(host, port=strategy.tcp_port, timeout=strategy.timeout)
            if ms > 0:
                lats.append(ms)
            await asyncio.sleep(strategy.interval)

        if not lats:
            continue

        avg = st.mean(lats)
        loss = ((strategy.count - len(lats)) / strategy.count) * 100

        # record into history
        hist.record(host, avg, loss)

        if avg < best_ms:
            best_ms = avg
            best_host = host

        # early stop: if a top-history server is still < 50ms, don't test all
        rec = hist.get(host)
        if rec and rec.score > 80 and avg < 50:
            result.history_informed = True
            break

    hist.save()

    if best_host:
        result.best_server = best_host
        result.best_latency = round(best_ms, 1)

    # 7 — recommendations
    result.recommendations = await generate_recommendations(game, region)

    return result


# ═════════════════════════════════════════════════════════════════════════════
#  8.  DNS INTELLIGENCE — History, Learning, Adaptive Selection
# ═════════════════════════════════════════════════════════════════════════════

class DNSHistory:
    """Persistent DNS performance history with EWMA learning."""

    _ALPHA = 0.3

    def __init__(self):
        self._records: Dict[str, DNSRecord] = {}
        self._load()

    def _load(self):
        p = _dns_history_path()
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text())
            for d in data:
                rec = DNSRecord.from_dict(d)
                self._records[rec.ip] = rec
        except Exception:
            pass

    def save(self):
        try:
            out = [r.to_dict() for r in self._records.values()]
            _dns_history_path().write_text(json.dumps(out, indent=1))
        except Exception:
            pass

    def record(self, provider: str, ip: str, latency_ms: float, reliable: bool):
        """Record one DNS benchmark result."""
        rec = self._records.get(ip)
        if not rec:
            rec = DNSRecord(provider=provider, ip=ip)
            self._records[ip] = rec

        a = self._ALPHA
        if rec.samples == 0:
            rec.avg_ms = latency_ms
            rec.reliability = 100.0 if reliable else 0.0
        else:
            rec.avg_ms = round(rec.avg_ms * (1 - a) + latency_ms * a, 2)
            rel_val = 100.0 if reliable else 0.0
            rec.reliability = round(rec.reliability * (1 - a) + rel_val * a, 1)

        rec.samples += 1
        rec.best_ms = min(rec.best_ms, latency_ms) if latency_ms > 0 else rec.best_ms
        rec.worst_ms = max(rec.worst_ms, latency_ms)
        rec.last_seen = time.time()
        rec.score = self._compute_score(rec)

    def _compute_score(self, r: DNSRecord) -> float:
        s = 100.0
        if r.avg_ms > 10:
            s -= min(40, (r.avg_ms - 10) * 0.8)
        s -= (100 - r.reliability) * 0.5
        spread = r.worst_ms - r.best_ms
        if spread > 20:
            s -= min(15, spread * 0.3)
        age_h = (time.time() - r.last_seen) / 3600 if r.last_seen else 999
        if age_h > 12:
            s -= min(10, age_h * 0.2)
        return round(max(0, min(100, s)), 1)

    def get(self, ip: str) -> Optional[DNSRecord]:
        return self._records.get(ip)

    def best_dns(self) -> Optional[DNSRecord]:
        """Return the historically best DNS server."""
        if not self._records:
            return None
        valid = [r for r in self._records.values() if r.samples >= 2 and r.reliability > 50]
        if not valid:
            return None
        return max(valid, key=lambda r: r.score)

    def ranked(self) -> List[DNSRecord]:
        """Return all DNS servers ranked by score."""
        known = [r for r in self._records.values() if r.samples > 0]
        known.sort(key=lambda r: r.score, reverse=True)
        return known

    def prune(self, max_age_days: int = 30):
        cutoff = time.time() - (max_age_days * 86400)
        self._records = {
            ip: r for ip, r in self._records.items() if r.last_seen > cutoff
        }


def choose_dns_strategy(condition: NetworkCondition) -> dict:
    """Adapt DNS benchmark parameters to network conditions."""
    if condition.quality in ("excellent", "good"):
        return {"count": 5, "timeout": 2.0, "reason": "Network stable — full DNS benchmark"}
    elif condition.quality == "fair":
        return {"count": 3, "timeout": 3.0, "reason": "Network fair — shorter DNS benchmark"}
    else:
        return {"count": 2, "timeout": 5.0, "reason": "Network degraded — minimal DNS probes"}


async def intelligent_dns_select(
    game: Optional[str] = None,
) -> Tuple[Optional[DNSRecord], List[SmartRecommendation]]:
    """
    Intelligent DNS selection: uses history + live benchmark + network condition.
    Returns (best_dns_record, recommendations).
    """
    recs: List[SmartRecommendation] = []
    dns_hist = DNSHistory()
    cond = await assess_network()
    strategy = choose_dns_strategy(cond)

    # Check if we have good historical data (< 6h old, high score)
    hist_best = dns_hist.best_dns()
    if hist_best and (time.time() - hist_best.last_seen) < 21600 and hist_best.score > 80:
        recs.append(SmartRecommendation(
            category="dns", priority=4,
            title=f"DNS historically best: {hist_best.provider}",
            detail=f"Score {hist_best.score}/100, avg {hist_best.avg_ms}ms ({hist_best.samples} sessions)",
            action_id=f"use_dns:{hist_best.ip}",
        ))

    # Run live benchmark on all DNS with adaptive parameters
    from dns_optimizer import benchmark_all_dns
    config = OptimizationConfig.load()
    config.dns_test_count = strategy["count"]
    config.dns_timeout = strategy["timeout"]

    # Use game-relevant test domains
    test_domains = ["google.com", "cloudflare.com"]
    if game and game in GAME_SERVERS:
        # Add a game-actual server as DNS resolution target
        for region_svs in GAME_SERVERS[game].values():
            for sv in region_svs:
                if not sv[0].isdigit():  # hostname, not IP
                    test_domains.append(sv)
                    break
            if len(test_domains) >= 4:
                break

    results = await benchmark_all_dns(config, test_domains=test_domains)

    # Record all results into history
    for r in results:
        dns_hist.record(r.name, r.primary_ip, r.avg_latency_ms if r.resolved_correctly else 999,
                        r.resolved_correctly)
    dns_hist.save()

    # Determine best: blend live result score with historical score
    best = None
    best_composite = -1
    for r in results:
        if not r.resolved_correctly:
            continue
        h = dns_hist.get(r.primary_ip)
        live_score = max(0, 100 - r.avg_latency_ms * 1.5)
        hist_score = h.score if h else 50
        composite = live_score * 0.6 + hist_score * 0.4
        if composite > best_composite:
            best_composite = composite
            best = h or DNSRecord(provider=r.name, ip=r.primary_ip, avg_ms=r.avg_latency_ms)

    # DNS-specific recommendations
    from dns_optimizer import get_current_dns
    current = get_current_dns()
    if best and current and current[0] != best.ip:
        recs.append(SmartRecommendation(
            category="dns", priority=2,
            title=f"Switch DNS to {best.provider} ({best.ip})",
            detail=f"Current DNS {current[0]} is slower. {best.provider} avg {best.avg_ms}ms, score {best.score}/100",
            action_id=f"set_dns:{best.ip}",
        ))

    if cond.quality in ("poor", "bad"):
        recs.append(SmartRecommendation(
            category="dns", priority=3,
            title="DNS accuracy may be affected by poor network",
            detail=f"Network quality is {cond.quality}. Re-run DNS benchmark when connection improves.",
            action_id="retry_dns",
        ))

    return best, recs


# ═════════════════════════════════════════════════════════════════════════════
#  9.  ROUTE INTELLIGENCE — History, Learning, Bottleneck Prediction
# ═════════════════════════════════════════════════════════════════════════════

class RouteHistory:
    """Persistent route performance history."""

    _ALPHA = 0.3

    def __init__(self):
        self._records: Dict[str, RouteRecord] = {}
        self._load()

    def _load(self):
        p = _route_history_path()
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text())
            for d in data:
                rec = RouteRecord.from_dict(d)
                self._records[rec.target] = rec
        except Exception:
            pass

    def save(self):
        try:
            out = [r.to_dict() for r in self._records.values()]
            _route_history_path().write_text(json.dumps(out, indent=1))
        except Exception:
            pass

    def record(self, target: str, hops: int, latency_ms: float,
               quality_score: float, bottleneck_ip: Optional[str] = None):
        """Record one route analysis result."""
        rec = self._records.get(target)
        if not rec:
            rec = RouteRecord(target=target)
            self._records[target] = rec

        a = self._ALPHA
        if rec.samples == 0:
            rec.avg_hops = hops
            rec.avg_latency_ms = latency_ms
            rec.avg_quality_score = quality_score
        else:
            rec.avg_hops = round(rec.avg_hops * (1 - a) + hops * a, 1)
            rec.avg_latency_ms = round(rec.avg_latency_ms * (1 - a) + latency_ms * a, 2)
            rec.avg_quality_score = round(rec.avg_quality_score * (1 - a) + quality_score * a, 1)

        rec.samples += 1
        rec.best_latency_ms = min(rec.best_latency_ms, latency_ms)
        rec.worst_latency_ms = max(rec.worst_latency_ms, latency_ms)
        rec.last_seen = time.time()

        if bottleneck_ip and bottleneck_ip not in rec.bottleneck_ips:
            rec.bottleneck_ips.append(bottleneck_ip)
            rec.bottleneck_ips = rec.bottleneck_ips[-5:]  # keep last 5

    def get(self, target: str) -> Optional[RouteRecord]:
        return self._records.get(target)

    def has_degraded(self, target: str, current_latency: float) -> bool:
        """Check if current route has degraded vs historical baseline."""
        rec = self._records.get(target)
        if not rec or rec.samples < 3:
            return False
        return current_latency > rec.avg_latency_ms * 1.5

    def prune(self, max_age_days: int = 30):
        cutoff = time.time() - (max_age_days * 86400)
        self._records = {
            t: r for t, r in self._records.items() if r.last_seen > cutoff
        }


def choose_route_strategy(condition: NetworkCondition) -> dict:
    """Adapt route analysis parameters to network conditions."""
    if condition.quality in ("excellent", "good"):
        return {"max_hops": 30, "timeout": 3.0, "reason": "Full route trace"}
    elif condition.quality == "fair":
        return {"max_hops": 25, "timeout": 4.0, "reason": "Moderate route trace"}
    else:
        return {"max_hops": 20, "timeout": 6.0, "reason": "Conservative route trace (poor network)"}


async def intelligent_route_analyze(
    target: str,
    game: Optional[str] = None,
) -> Tuple[Optional[object], List[SmartRecommendation]]:
    """
    Intelligent route analysis with history comparison and adaptive parameters.
    Returns (route_analysis, recommendations).
    """
    from route_optimizer import analyze_route
    recs: List[SmartRecommendation] = []
    route_hist = RouteHistory()
    cond = await assess_network()
    strategy = choose_route_strategy(cond)

    config = OptimizationConfig.load()
    config.max_hops = strategy["max_hops"]

    route = await analyze_route(target, config)

    # Quality score mapping
    q_map = {"excellent": 95, "good": 75, "fair": 50, "poor": 25}
    quality_score = q_map.get(route.route_quality, 25)

    bottleneck_ip = None
    if route.bottleneck_hop and route.bottleneck_hop.ip:
        bottleneck_ip = route.bottleneck_hop.ip

    # Record into history
    route_hist.record(target, route.total_hops, route.avg_latency, quality_score, bottleneck_ip)
    route_hist.save()

    # Compare with history
    hist_rec = route_hist.get(target)
    if hist_rec and hist_rec.samples >= 3:
        if route_hist.has_degraded(target, route.avg_latency):
            recs.append(SmartRecommendation(
                category="route", priority=2,
                title="Route degradation detected",
                detail=(
                    f"Current latency {route.avg_latency}ms vs historical avg "
                    f"{hist_rec.avg_latency_ms}ms (+{route.avg_latency - hist_rec.avg_latency_ms:.0f}ms). "
                    "Network conditions may have changed."
                ),
                action_id="diagnose_route",
            ))

        if hist_rec.bottleneck_ips and bottleneck_ip and bottleneck_ip in hist_rec.bottleneck_ips:
            recs.append(SmartRecommendation(
                category="route", priority=2,
                title=f"Recurring bottleneck at {bottleneck_ip}",
                detail=(
                    f"This IP has been a bottleneck in {len(hist_rec.bottleneck_ips)} "
                    "previous scans. Consider using a VPN to route around it."
                ),
                action_id="suggest_vpn",
            ))

    if route.route_quality == "poor":
        recs.append(SmartRecommendation(
            category="route", priority=1,
            title="Poor route quality",
            detail=f"Route to {target} has {route.total_hops} hops and {route.avg_latency}ms avg. Try a different server or VPN.",
            action_id="switch_server",
        ))

    if route.bottleneck_hop and route.bottleneck_hop.latency_ms > 100:
        recs.append(SmartRecommendation(
            category="route", priority=2,
            title=f"Major bottleneck at hop {route.bottleneck_hop.hop_number}",
            detail=f"Hop {route.bottleneck_hop.hop_number} ({route.bottleneck_hop.ip or '???'}) adds {route.bottleneck_hop.latency_ms}ms",
            action_id="analyze_bottleneck",
        ))

    return route, recs


# ═════════════════════════════════════════════════════════════════════════════
# 10.  TCP/UDP INTELLIGENT TUNING
# ═════════════════════════════════════════════════════════════════════════════

def intelligent_socket_config(
    condition: NetworkCondition,
    game: Optional[str] = None,
) -> Tuple[AdaptiveSocketConfig, List[SmartRecommendation]]:
    """
    Dynamically adapt socket parameters based on network condition and game.
    """
    recs: List[SmartRecommendation] = []
    cfg = AdaptiveSocketConfig()

    # Start from game profile defaults
    from tcp_udp_tuner import GAME_PROFILE_MAP, GAMING_PROFILES
    profile_key = GAME_PROFILE_MAP.get(game, "competitive_fps") if game else "competitive_fps"
    base_profile = GAMING_PROFILES[profile_key]

    cfg.tcp_nodelay = base_profile.tcp_nodelay
    cfg.tcp_quickack = base_profile.tcp_quickack
    cfg.recv_buffer = base_profile.recv_buffer
    cfg.send_buffer = base_profile.send_buffer
    cfg.keep_alive_interval = base_profile.keep_alive_interval

    # Adapt based on network condition
    q = condition.quality

    if q in ("poor", "bad"):
        # Larger buffers to handle bursts; longer keepalive to avoid reconnects
        cfg.recv_buffer = max(cfg.recv_buffer, 1048576)
        cfg.send_buffer = max(cfg.send_buffer, 524288)
        cfg.keep_alive_interval = 10
        cfg.reason = "Network degraded — larger buffers for burst handling, aggressive keepalive"
        recs.append(SmartRecommendation(
            category="socket", priority=2,
            title="Enlarged socket buffers for poor network",
            detail=f"Recv={cfg.recv_buffer:,}B, Send={cfg.send_buffer:,}B to handle packet bursts",
            action_id="apply_socket_tune",
        ))
    elif q == "fair":
        cfg.recv_buffer = max(cfg.recv_buffer, 524288)
        cfg.send_buffer = max(cfg.send_buffer, 524288)
        cfg.keep_alive_interval = 15
        cfg.reason = "Network fair — moderate buffers with quick keepalive"
    elif q in ("excellent", "good"):
        # Smaller buffers for minimal latency
        if game in ("valorant", "cs2", "overwatch2"):
            cfg.recv_buffer = min(cfg.recv_buffer, 262144)
            cfg.send_buffer = min(cfg.send_buffer, 262144)
            cfg.reason = "Network excellent + FPS — minimal buffers for lowest latency"
        else:
            cfg.reason = "Network good — using game profile defaults"

    # Jitter-specific tuning
    if condition.jitter_ms > 20:
        cfg.recv_buffer = max(cfg.recv_buffer, 524288)
        recs.append(SmartRecommendation(
            category="socket", priority=3,
            title="High jitter: increased receive buffer",
            detail=f"Jitter {condition.jitter_ms}ms — larger recv buffer ({cfg.recv_buffer:,}B) smooths delivery",
            action_id="apply_socket_tune",
        ))

    # Loss-specific tuning
    if condition.loss_pct > 5:
        cfg.keep_alive_interval = 5
        recs.append(SmartRecommendation(
            category="socket", priority=2,
            title="Packet loss: aggressive keepalive",
            detail=f"Loss {condition.loss_pct}% — keepalive every {cfg.keep_alive_interval}s for quick reconnection",
            action_id="apply_socket_tune",
        ))

    return cfg, recs


# ═════════════════════════════════════════════════════════════════════════════
# 11.  OS OPTIMIZATION INTELLIGENCE
# ═════════════════════════════════════════════════════════════════════════════

def intelligent_os_config(
    condition: NetworkCondition,
    game: Optional[str] = None,
) -> Tuple[AdaptiveOSConfig, List[SmartRecommendation]]:
    """
    Select which OS optimizations to apply based on network conditions.
    Returns indices into get_optimizations() list and recommendations.
    """
    from os_optimizer import get_optimizations, read_current_values
    recs: List[SmartRecommendation] = []
    cfg = AdaptiveOSConfig()

    opts = get_optimizations()
    opts = read_current_values(opts)
    q = condition.quality

    for i, opt in enumerate(opts):
        # Always recommend: delayed ACK disable, TCP Fast Open, buffer sizes
        name_lower = opt.name.lower()
        if any(kw in name_lower for kw in ("delayed ack", "fast open", "buffer", "nagle")):
            cfg.recommended_indices.append(i)
            continue

        # Network-condition gated
        if "power sav" in name_lower or "wi-fi" in name_lower:
            if condition.jitter_ms > 10 or q in ("fair", "poor", "bad"):
                cfg.recommended_indices.append(i)
                recs.append(SmartRecommendation(
                    category="system", priority=3,
                    title=f"Recommend: {opt.name}",
                    detail=f"Jitter {condition.jitter_ms}ms suggests Wi-Fi power management issues",
                    action_id=f"apply_os:{i}",
                ))
            else:
                cfg.skip_indices.append(i)
            continue

        if "low latency" in name_lower:
            if q in ("fair", "poor", "bad") or (game and game in ("valorant", "cs2", "overwatch2")):
                cfg.recommended_indices.append(i)
            else:
                cfg.skip_indices.append(i)
            continue

        if "congestion" in name_lower or "bbr" in name_lower:
            if condition.loss_pct > 3:
                cfg.recommended_indices.append(i)
                recs.append(SmartRecommendation(
                    category="system", priority=2,
                    title=f"Recommend: {opt.name}",
                    detail=f"Loss {condition.loss_pct}% — BBR congestion control handles loss better",
                    action_id=f"apply_os:{i}",
                ))
            else:
                cfg.recommended_indices.append(i)
            continue

        if "throttl" in name_lower or "gaming priority" in name_lower:
            if game:
                cfg.recommended_indices.append(i)
            else:
                cfg.skip_indices.append(i)
            continue

        if "timestamp" in name_lower or "sack" in name_lower:
            # Only disable on excellent networks — they add safety on bad networks
            if q in ("excellent", "good"):
                cfg.recommended_indices.append(i)
            else:
                cfg.skip_indices.append(i)
                recs.append(SmartRecommendation(
                    category="system", priority=4,
                    title=f"Skipping: {opt.name}",
                    detail=f"Network is {q} — keeping safety features enabled",
                    action_id=f"skip_os:{i}",
                ))
            continue

        # Default: recommend
        cfg.recommended_indices.append(i)

    if q in ("excellent", "good"):
        cfg.reason = f"Network {q} — applying all optimizations for maximum performance"
    elif q == "fair":
        cfg.reason = "Network fair — selective optimizations, keeping safety nets"
    else:
        cfg.reason = f"Network {q} — conservative optimizations, preserving stability features"

    return cfg, recs


# ═════════════════════════════════════════════════════════════════════════════
# 12.  INTELLIGENT MONITORING — Anomaly Detection & Pattern Analysis
# ═════════════════════════════════════════════════════════════════════════════

class IntelligentMonitor:
    """
    Wraps ping monitoring with anomaly detection, pattern recognition,
    and adaptive thresholds.
    """

    def __init__(self):
        self._baseline_ms: Optional[float] = None
        self._baseline_jitter: Optional[float] = None
        self._anomalies: List[MonitorAnomaly] = []
        self._recent_latencies: deque = deque(maxlen=50)
        self._consecutive_spikes: int = 0
        self._consecutive_drops: int = 0
        self._load_baseline()

    def _load_baseline(self):
        """Load historical baseline from disk."""
        p = _netcond_path()
        if not p.exists():
            return
        try:
            d = json.loads(p.read_text())
            self._baseline_ms = d.get("base_latency_ms")
            self._baseline_jitter = d.get("jitter_ms")
        except Exception:
            pass

    def analyze_snapshot(self, latency_ms: float, is_timeout: bool) -> Optional[MonitorAnomaly]:
        """
        Analyze a single ping measurement for anomalies.
        Returns an anomaly if detected, None otherwise.
        """
        anomaly = None

        if is_timeout:
            self._consecutive_drops += 1
            self._consecutive_spikes = 0

            if self._consecutive_drops >= 3:
                anomaly = MonitorAnomaly(
                    timestamp=time.time(),
                    anomaly_type="dropout",
                    severity="critical" if self._consecutive_drops >= 5 else "high",
                    detail=f"{self._consecutive_drops} consecutive timeouts — possible connection loss",
                    value=self._consecutive_drops,
                )
        else:
            self._consecutive_drops = 0
            self._recent_latencies.append(latency_ms)

            # Spike detection (adaptive threshold)
            if len(self._recent_latencies) >= 5:
                recent_avg = st.mean(list(self._recent_latencies)[-20:])
                spike_threshold = max(recent_avg * 2.0, (self._baseline_ms or 50) * 2.5)

                if latency_ms > spike_threshold:
                    self._consecutive_spikes += 1
                    severity = "high" if latency_ms > spike_threshold * 1.5 else "medium"
                    anomaly = MonitorAnomaly(
                        timestamp=time.time(),
                        anomaly_type="spike",
                        severity=severity,
                        detail=f"Latency spike: {latency_ms:.1f}ms (threshold {spike_threshold:.1f}ms)",
                        value=latency_ms,
                    )
                else:
                    self._consecutive_spikes = 0

            # Jitter burst detection
            if len(self._recent_latencies) >= 10:
                recent = list(self._recent_latencies)[-10:]
                diffs = [abs(recent[i] - recent[i-1]) for i in range(1, len(recent))]
                recent_jitter = st.mean(diffs)
                jitter_threshold = max(15, (self._baseline_jitter or 10) * 3)

                if recent_jitter > jitter_threshold and not anomaly:
                    anomaly = MonitorAnomaly(
                        timestamp=time.time(),
                        anomaly_type="jitter_burst",
                        severity="medium",
                        detail=f"Jitter burst: {recent_jitter:.1f}ms avg (threshold {jitter_threshold:.1f}ms)",
                        value=recent_jitter,
                    )

            # Gradual degradation detection
            if len(self._recent_latencies) >= 30 and self._baseline_ms:
                recent_avg = st.mean(list(self._recent_latencies)[-15:])
                older_avg = st.mean(list(self._recent_latencies)[-30:-15])
                if recent_avg > older_avg * 1.4 and recent_avg > self._baseline_ms * 1.5:
                    if not anomaly:
                        anomaly = MonitorAnomaly(
                            timestamp=time.time(),
                            anomaly_type="degradation",
                            severity="medium",
                            detail=(
                                f"Gradual degradation: recent {recent_avg:.1f}ms "
                                f"vs earlier {older_avg:.1f}ms (baseline {self._baseline_ms:.1f}ms)"
                            ),
                            value=recent_avg,
                        )

        if anomaly:
            self._anomalies.append(anomaly)
            self._anomalies = self._anomalies[-100:]  # keep last 100

        return anomaly

    def get_pattern_summary(self) -> str:
        """Summarize detected patterns."""
        if not self._anomalies:
            return "No anomalies detected — connection is stable."

        counts = {}
        for a in self._anomalies:
            counts[a.anomaly_type] = counts.get(a.anomaly_type, 0) + 1

        parts = []
        for atype, count in sorted(counts.items(), key=lambda x: -x[1]):
            label = {"spike": "Latency spikes", "dropout": "Connection dropouts",
                     "jitter_burst": "Jitter bursts", "degradation": "Gradual degradations"}.get(atype, atype)
            parts.append(f"{label}: {count}")
        return " | ".join(parts)

    def get_recommendations(self) -> List[SmartRecommendation]:
        """Generate recommendations from detected anomalies."""
        recs = []
        if not self._anomalies:
            return recs

        counts = {}
        for a in self._anomalies:
            counts[a.anomaly_type] = counts.get(a.anomaly_type, 0) + 1

        if counts.get("dropout", 0) >= 3:
            recs.append(SmartRecommendation(
                category="system", priority=1,
                title="Frequent connection drops detected",
                detail="Multiple timeouts detected. Check cable/Wi-Fi, or switch to wired connection.",
                action_id="check_connection",
            ))

        if counts.get("spike", 0) >= 5:
            recs.append(SmartRecommendation(
                category="system", priority=2,
                title="Frequent latency spikes",
                detail="Recurring spikes suggest background traffic or ISP issues. Close bandwidth-heavy apps.",
                action_id="apply_os_tweaks",
            ))

        if counts.get("jitter_burst", 0) >= 3:
            recs.append(SmartRecommendation(
                category="system", priority=2,
                title="Unstable connection (jitter bursts)",
                detail="High jitter detected. Try disabling Wi-Fi power saving and enabling QoS.",
                action_id="apply_os_tweaks",
            ))

        if counts.get("degradation", 0) >= 2:
            recs.append(SmartRecommendation(
                category="system", priority=3,
                title="Connection quality declining over time",
                detail="Latency is gradually increasing. This may indicate thermal throttling or ISP congestion.",
                action_id="diagnose_network",
            ))

        return recs

    @property
    def anomalies(self) -> List[MonitorAnomaly]:
        return list(self._anomalies)


def choose_monitor_strategy(condition: NetworkCondition) -> dict:
    """Adapt monitoring parameters based on network conditions."""
    if condition.quality in ("excellent", "good"):
        return {
            "interval": 0.5,
            "spike_threshold": 2.5,
            "reason": "Network stable — fast monitoring, relaxed spike detection",
        }
    elif condition.quality == "fair":
        return {
            "interval": 0.8,
            "spike_threshold": 2.0,
            "reason": "Network fair — moderate monitoring",
        }
    else:
        return {
            "interval": 1.0,
            "spike_threshold": 1.5,
            "reason": "Network degraded — slower monitoring, tight spike detection",
        }


# ═════════════════════════════════════════════════════════════════════════════
# 13.  ADAPTIVE SCANNER — Intelligent ping parameters for scan_servers
# ═════════════════════════════════════════════════════════════════════════════

def adaptive_scan_config(
    condition: NetworkCondition,
    game: Optional[str] = None,
) -> OptimizationConfig:
    """
    Return an OptimizationConfig with adaptive ping parameters
    based on current network condition.
    """
    config = OptimizationConfig.load()
    q = condition.quality

    if q == "excellent":
        config.ping_count = 15
        config.ping_interval = 0.3
        config.ping_timeout = 1.5
    elif q == "good":
        config.ping_count = 10
        config.ping_interval = 0.4
        config.ping_timeout = 2.0
    elif q == "fair":
        config.ping_count = 8
        config.ping_interval = 0.6
        config.ping_timeout = 3.0
    else:
        config.ping_count = 5
        config.ping_interval = 1.0
        config.ping_timeout = 5.0

    return config


# ═════════════════════════════════════════════════════════════════════════════
# 14.  FULL INTELLIGENT OPTIMIZATION — All subsystems unified
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class FullIntelligentResult:
    """Complete result from intelligent optimization of all subsystems."""

    # Server
    best_server: Optional[str] = None
    best_latency: float = -1
    region_used: str = ""
    history_informed: bool = False

    # DNS
    best_dns: Optional[DNSRecord] = None

    # Route
    route_analysis: Optional[object] = None
    route_degraded: bool = False

    # Socket
    socket_config: Optional[AdaptiveSocketConfig] = None

    # OS
    os_config: Optional[AdaptiveOSConfig] = None

    # Network condition
    network_condition: Optional[NetworkCondition] = None
    ping_strategy: Optional[PingStrategy] = None

    # Game
    running_game: Optional[DetectedGame] = None

    # All recommendations (merged from all subsystems)
    recommendations: List[SmartRecommendation] = field(default_factory=list)

    # MTU
    optimal_mtu: int = 1500


async def full_intelligent_optimize(
    game: Optional[str] = None,
    region: Optional[str] = None,
) -> FullIntelligentResult:
    """
    Unified intelligent optimization across ALL subsystems:
      1. Detect running game
      2. Detect region
      3. Assess network condition
      4. Adaptive server selection (with history)
      5. Intelligent DNS benchmark and selection
      6. Intelligent route analysis (with history)
      7. Adaptive TCP/UDP tuning
      8. Intelligent OS optimization selection
      9. Merge all recommendations
    """
    result = FullIntelligentResult()
    all_recs: List[SmartRecommendation] = []

    # 1 — detect game
    if not game:
        detected = detect_running_games()
        if detected:
            game = detected[0].name
            result.running_game = detected[0]

    # 2 — detect region
    if not region:
        geo = detect_region()
        if geo.confidence < 0.5:
            region = await detect_region_by_latency()
        else:
            region = geo.region_code
    result.region_used = region or "NA"

    # 3 — network condition
    cond = await assess_network()
    result.network_condition = cond

    # 4 — adaptive server selection
    server_result = await smart_select(game, region)
    result.best_server = server_result.best_server
    result.best_latency = server_result.best_latency
    result.history_informed = server_result.history_informed
    result.ping_strategy = server_result.ping_strategy
    all_recs.extend(server_result.recommendations)

    # 5 — intelligent DNS
    best_dns, dns_recs = await intelligent_dns_select(game)
    result.best_dns = best_dns
    all_recs.extend(dns_recs)

    # 6 — intelligent route analysis
    target = result.best_server or "8.8.8.8"
    route, route_recs = await intelligent_route_analyze(target, game)
    result.route_analysis = route
    if route:
        from route_optimizer import RouteAnalysis
        if hasattr(route, 'avg_latency'):
            route_hist = RouteHistory()
            rec = route_hist.get(target)
            if rec and rec.samples >= 3:
                result.route_degraded = route_hist.has_degraded(target, route.avg_latency)
    all_recs.extend(route_recs)

    # 7 — intelligent socket tuning
    socket_cfg, socket_recs = intelligent_socket_config(cond, game)
    result.socket_config = socket_cfg
    all_recs.extend(socket_recs)

    # 8 — intelligent OS optimization
    os_cfg, os_recs = intelligent_os_config(cond, game)
    result.os_config = os_cfg
    all_recs.extend(os_recs)

    # 9 — optimal MTU
    if result.best_server:
        from route_optimizer import find_optimal_mtu
        result.optimal_mtu = await find_optimal_mtu(result.best_server)

    # Deduplicate and sort recommendations
    seen_ids = set()
    unique_recs = []
    for r in sorted(all_recs, key=lambda x: x.priority):
        if r.action_id not in seen_ids:
            unique_recs.append(r)
            seen_ids.add(r.action_id)
    result.recommendations = unique_recs

    return result
