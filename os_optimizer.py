"""
UltimatePing - OS Network Optimizer
Applies system-level network optimizations for gaming.
Supports macOS, Linux, and Windows.
"""

import platform
import subprocess
import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class SystemOptimization:
    """Represents a single system optimization."""

    name: str
    description: str
    command: str
    revert_command: str
    requires_admin: bool
    current_value: Optional[str] = None
    target_value: Optional[str] = None


def _run_cmd(cmd: str, timeout: int = 10) -> Tuple[bool, str]:
    """Run a shell command safely and return (success, output)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return (result.returncode == 0, result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return (False, "")


def get_os_type() -> str:
    return platform.system().lower()


# ─── macOS Optimizations ────────────────────────────────────────────────────

def _macos_optimizations() -> List[SystemOptimization]:
    """Generate macOS-specific network optimizations."""
    opts: List[SystemOptimization] = []

    # TCP delayed ACK - disable for lower latency
    opts.append(SystemOptimization(
        name="Disable TCP Delayed ACK",
        description="Sends ACK immediately instead of waiting. Reduces latency by ~40ms.",
        command="sudo sysctl -w net.inet.tcp.delayed_ack=0",
        revert_command="sudo sysctl -w net.inet.tcp.delayed_ack=3",
        requires_admin=True,
    ))

    # Increase socket buffer sizes
    opts.append(SystemOptimization(
        name="Increase TCP Send Buffer",
        description="Larger send buffer reduces send-side stalls.",
        command="sudo sysctl -w net.inet.tcp.sendspace=262144",
        revert_command="sudo sysctl -w net.inet.tcp.sendspace=131072",
        requires_admin=True,
    ))

    opts.append(SystemOptimization(
        name="Increase TCP Receive Buffer",
        description="Larger receive buffer handles burst traffic better.",
        command="sudo sysctl -w net.inet.tcp.recvspace=262144",
        revert_command="sudo sysctl -w net.inet.tcp.recvspace=131072",
        requires_admin=True,
    ))

    # Enable TCP Fast Open
    opts.append(SystemOptimization(
        name="Enable TCP Fast Open",
        description="Allows data in SYN packet, reducing connection time.",
        command="sudo sysctl -w net.inet.tcp.fastopen=3",
        revert_command="sudo sysctl -w net.inet.tcp.fastopen=0",
        requires_admin=True,
    ))

    # Reduce keepalive interval
    opts.append(SystemOptimization(
        name="Reduce TCP Keepalive",
        description="Faster detection of dead connections.",
        command="sudo sysctl -w net.inet.tcp.keepidle=10000",
        revert_command="sudo sysctl -w net.inet.tcp.keepidle=7200000",
        requires_admin=True,
    ))

    # Increase max socket buffer
    opts.append(SystemOptimization(
        name="Increase Max Socket Buffer",
        description="Allows applications to use larger buffers.",
        command="sudo sysctl -w kern.ipc.maxsockbuf=4194304",
        revert_command="sudo sysctl -w kern.ipc.maxsockbuf=2097152",
        requires_admin=True,
    ))

    # Disable power nap network (Wi-Fi)
    opts.append(SystemOptimization(
        name="Disable Wi-Fi Power Saving",
        description="Prevents Wi-Fi from sleeping, reducing reconnect latency.",
        command="sudo /usr/libexec/airportd setpowersavemode off 2>/dev/null || true",
        revert_command="sudo /usr/libexec/airportd setpowersavemode on 2>/dev/null || true",
        requires_admin=True,
    ))

    return opts


# ─── Linux Optimizations ────────────────────────────────────────────────────

def _linux_optimizations() -> List[SystemOptimization]:
    """Generate Linux-specific network optimizations."""
    opts: List[SystemOptimization] = []

    # TCP congestion control - BBR
    opts.append(SystemOptimization(
        name="Enable BBR Congestion Control",
        description="Google's BBR provides better throughput and lower latency.",
        command="sudo sysctl -w net.ipv4.tcp_congestion_control=bbr",
        revert_command="sudo sysctl -w net.ipv4.tcp_congestion_control=cubic",
        requires_admin=True,
    ))

    # Enable TCP Fast Open
    opts.append(SystemOptimization(
        name="Enable TCP Fast Open",
        description="Allows data in SYN packet for faster connections.",
        command="sudo sysctl -w net.ipv4.tcp_fastopen=3",
        revert_command="sudo sysctl -w net.ipv4.tcp_fastopen=0",
        requires_admin=True,
    ))

    # Disable TCP timestamps (reduces header overhead)
    opts.append(SystemOptimization(
        name="Disable TCP Timestamps",
        description="Reduces overhead per packet by ~12 bytes.",
        command="sudo sysctl -w net.ipv4.tcp_timestamps=0",
        revert_command="sudo sysctl -w net.ipv4.tcp_timestamps=1",
        requires_admin=True,
    ))

    # TCP low latency mode
    opts.append(SystemOptimization(
        name="Enable TCP Low Latency",
        description="Prioritizes latency over throughput.",
        command="sudo sysctl -w net.ipv4.tcp_low_latency=1",
        revert_command="sudo sysctl -w net.ipv4.tcp_low_latency=0",
        requires_admin=True,
    ))

    # Increase buffer sizes
    opts.append(SystemOptimization(
        name="Optimize TCP Buffer Sizes",
        description="Set optimal min/default/max buffer sizes.",
        command="sudo sysctl -w net.ipv4.tcp_rmem='4096 262144 4194304' && sudo sysctl -w net.ipv4.tcp_wmem='4096 262144 4194304'",
        revert_command="sudo sysctl -w net.ipv4.tcp_rmem='4096 131072 6291456' && sudo sysctl -w net.ipv4.tcp_wmem='4096 16384 4194304'",
        requires_admin=True,
    ))

    # Reduce TCP FIN timeout
    opts.append(SystemOptimization(
        name="Reduce TCP FIN Timeout",
        description="Faster cleanup of closed connections.",
        command="sudo sysctl -w net.ipv4.tcp_fin_timeout=15",
        revert_command="sudo sysctl -w net.ipv4.tcp_fin_timeout=60",
        requires_admin=True,
    ))

    # Disable TCP SACK (can add latency)
    opts.append(SystemOptimization(
        name="Disable TCP Selective ACK",
        description="Removes SACK overhead for gaming traffic.",
        command="sudo sysctl -w net.ipv4.tcp_sack=0",
        revert_command="sudo sysctl -w net.ipv4.tcp_sack=1",
        requires_admin=True,
    ))

    # Increase netdev budget
    opts.append(SystemOptimization(
        name="Increase Network Device Budget",
        description="Process more packets per CPU cycle.",
        command="sudo sysctl -w net.core.netdev_budget=600",
        revert_command="sudo sysctl -w net.core.netdev_budget=300",
        requires_admin=True,
    ))

    # Disable offloading features that add latency
    # Detect primary interface
    ok, iface = _run_cmd("ip route show default | awk '{print $5}' | head -1")
    if ok and iface:
        if shutil.which("ethtool"):
            opts.append(SystemOptimization(
                name=f"Disable GRO on {iface}",
                description="Generic Receive Offload can add buffering latency.",
                command=f"sudo ethtool -K {iface} gro off",
                revert_command=f"sudo ethtool -K {iface} gro on",
                requires_admin=True,
            ))

    return opts


# ─── Windows Optimizations ──────────────────────────────────────────────────

def _windows_optimizations() -> List[SystemOptimization]:
    """Generate Windows-specific network optimizations."""
    opts: List[SystemOptimization] = []

    # Disable Nagle's Algorithm globally
    opts.append(SystemOptimization(
        name="Disable Nagle's Algorithm",
        description="Sends packets immediately without batching.",
        command='netsh int tcp set global naglealgorithm=disabled',
        revert_command='netsh int tcp set global naglealgorithm=enabled',
        requires_admin=True,
    ))

    # Enable Direct Cache Access
    opts.append(SystemOptimization(
        name="Enable DCA",
        description="Allows direct memory access for network data.",
        command='netsh int tcp set global dca=enabled',
        revert_command='netsh int tcp set global dca=disabled',
        requires_admin=True,
    ))

    # Disable Auto-tuning
    opts.append(SystemOptimization(
        name="Set Receive Window to Normal",
        description="Prevents auto-tuning from adding latency.",
        command='netsh int tcp set global autotuninglevel=normal',
        revert_command='netsh int tcp set global autotuninglevel=normal',
        requires_admin=True,
    ))

    # Disable ECN
    opts.append(SystemOptimization(
        name="Disable ECN Capability",
        description="ECN can cause issues with some game servers.",
        command='netsh int tcp set global ecncapability=disabled',
        revert_command='netsh int tcp set global ecncapability=default',
        requires_admin=True,
    ))

    # Disable TCP chimney
    opts.append(SystemOptimization(
        name="Disable TCP Chimney Offload",
        description="Prevents offload-related latency spikes.",
        command='netsh int tcp set global chimney=disabled',
        revert_command='netsh int tcp set global chimney=enabled',
        requires_admin=True,
    ))

    # Flush DNS
    opts.append(SystemOptimization(
        name="Flush DNS Cache",
        description="Clear stale DNS entries.",
        command='ipconfig /flushdns',
        revert_command='echo No revert needed',
        requires_admin=True,
    ))

    # Disable network throttling
    opts.append(SystemOptimization(
        name="Disable Network Throttling Index",
        description="Prevents Windows from throttling network for multimedia.",
        command='reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile" /v NetworkThrottlingIndex /t REG_DWORD /d 0xffffffff /f',
        revert_command='reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile" /v NetworkThrottlingIndex /t REG_DWORD /d 10 /f',
        requires_admin=True,
    ))

    # Gaming priority
    opts.append(SystemOptimization(
        name="Set Gaming Network Priority",
        description="Prioritize game traffic in the network stack.",
        command='reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games" /v Priority /t REG_DWORD /d 6 /f',
        revert_command='reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile\\Tasks\\Games" /v Priority /t REG_DWORD /d 2 /f',
        requires_admin=True,
    ))

    return opts


def get_optimizations() -> List[SystemOptimization]:
    """Get optimizations for the current OS."""
    system = get_os_type()
    if system == "darwin":
        return _macos_optimizations()
    elif system == "linux":
        return _linux_optimizations()
    elif system == "windows":
        return _windows_optimizations()
    return []


def read_current_values(
    optimizations: List[SystemOptimization],
) -> List[SystemOptimization]:
    """Read current system values for each optimization."""
    system = get_os_type()

    for opt in optimizations:
        if system in ("darwin", "linux") and "sysctl" in opt.command:
            # Extract sysctl key
            parts = opt.command.split()
            for i, p in enumerate(parts):
                if p == "-w" and i + 1 < len(parts):
                    key_val = parts[i + 1]
                    key = key_val.split("=")[0]
                    ok, val = _run_cmd(f"sysctl -n {key}")
                    if ok:
                        opt.current_value = val
                        opt.target_value = key_val.split("=")[1] if "=" in key_val else None
                    break
    return optimizations


def apply_optimization(opt: SystemOptimization) -> Tuple[bool, str]:
    """Apply a single optimization. Returns (success, message)."""
    ok, output = _run_cmd(opt.command)
    if ok:
        return (True, f"Applied: {opt.name}")
    return (False, f"Failed: {opt.name} - {output}")


def revert_optimization(opt: SystemOptimization) -> Tuple[bool, str]:
    """Revert a single optimization. Returns (success, message)."""
    ok, output = _run_cmd(opt.revert_command)
    if ok:
        return (True, f"Reverted: {opt.name}")
    return (False, f"Failed to revert: {opt.name} - {output}")


def apply_all_optimizations() -> List[Tuple[bool, str]]:
    """Apply all optimizations for the current OS."""
    opts = get_optimizations()
    results = []
    for opt in opts:
        results.append(apply_optimization(opt))
    return results


def apply_intelligent_optimizations(
    game: Optional[str] = None,
) -> Tuple[List[Tuple[bool, str]], List[str]]:
    """
    Apply only the optimizations recommended by the intelligence engine.
    Returns (results, skipped_names).
    """
    try:
        import asyncio
        from intelligence import assess_network, intelligent_os_config

        loop = asyncio.new_event_loop()
        cond = loop.run_until_complete(assess_network())
        loop.close()

        os_cfg, _ = intelligent_os_config(cond, game)
        opts = get_optimizations()
        results = []
        skipped = []

        for i, opt in enumerate(opts):
            if i in os_cfg.recommended_indices:
                results.append(apply_optimization(opt))
            else:
                skipped.append(opt.name)

        return results, skipped
    except Exception:
        # Fallback to applying all
        return apply_all_optimizations(), []


def revert_all_optimizations() -> List[Tuple[bool, str]]:
    """Revert all optimizations for the current OS."""
    opts = get_optimizations()
    results = []
    for opt in opts:
        results.append(revert_optimization(opt))
    return results


def generate_optimization_script() -> str:
    """Generate a shell script with all optimizations."""
    system = get_os_type()
    opts = get_optimizations()

    if system == "windows":
        script = "@echo off\nREM UltimatePing Network Optimizations\n"
        script += "REM Run as Administrator\n\n"
        for opt in opts:
            script += f"REM {opt.name}: {opt.description}\n"
            script += f"{opt.command}\n\n"
        script += "echo All optimizations applied!\npause\n"
    else:
        script = "#!/bin/bash\n# UltimatePing Network Optimizations\n"
        script += "# Run with sudo\n\n"
        script += "set -e\n\n"
        for opt in opts:
            script += f"# {opt.name}: {opt.description}\n"
            script += f"{opt.command}\n\n"
        script += 'echo "All optimizations applied!"\n'

    return script


def generate_revert_script() -> str:
    """Generate a shell script to revert all optimizations."""
    system = get_os_type()
    opts = get_optimizations()

    if system == "windows":
        script = "@echo off\nREM UltimatePing Revert Optimizations\n\n"
        for opt in opts:
            script += f"REM Revert: {opt.name}\n"
            script += f"{opt.revert_command}\n\n"
        script += "echo All settings reverted!\npause\n"
    else:
        script = "#!/bin/bash\n# UltimatePing Revert Optimizations\n\n"
        script += "set -e\n\n"
        for opt in opts:
            script += f"# Revert: {opt.name}\n"
            script += f"{opt.revert_command}\n\n"
        script += 'echo "All settings reverted!"\n'

    return script
