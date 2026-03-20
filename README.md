# UltimatePing — Ultimate Gaming Network Optimizer

**Better than ExitLag — Free, Open Source, No Subscription**

A Python-based network optimization tool that reduces ping and improves connection quality for online gaming. Works on **macOS, Linux, and Windows**.

---

## Features

| Feature | Description |
|---------|-------------|
| **Full Game Optimization** | One-click optimization for popular games (Valorant, CS2, LoL, Fortnite, etc.) |
| **Server Scanner** | Tests all game servers and finds the lowest-latency one |
| **DNS Optimizer** | Benchmarks 8+ DNS providers and finds the fastest |
| **Route Analyzer** | Traceroute with bottleneck detection and multi-path analysis |
| **Real-time Monitor** | Live ping monitoring with jitter, spike detection, and stability scoring |
| **System Optimizer** | OS-level TCP/UDP tuning (delayed ACK, BBR, buffer sizes, etc.) |
| **Socket Tuning** | Game-specific socket profiles (FPS, MOBA, Battle Royale, MMO) |
| **MTU Optimizer** | Finds optimal MTU to prevent fragmentation |
| **Script Generator** | Creates apply/revert scripts for system optimizations |

## Supported Games

- Valorant
- Counter-Strike 2
- League of Legends
- Fortnite
- Apex Legends
- Overwatch 2
- DOTA 2
- PUBG
- Custom servers (any IP/hostname)

## Quick Start

```bash
# CLI mode (terminal)
python3 main.py

# GUI mode (graphical window — best on Windows)
python3 main.py --gui
# or directly:
python3 gui.py
```

## GUI Mode (Windows-Focused)

Premium graphical interface built with **CustomTkinter** — modern rounded widgets, dark gaming aesthetic with indigo/cyan accents, sidebar navigation, real-time ping graphs, and toast notifications. Designed for Windows but works cross-platform.

### Screenshots Overview

The GUI has 7 pages accessible from the sidebar:

| Page | Features |
|------|----------|
| **Dashboard** | Stats cards (ping/jitter/loss/stability), quick-action buttons, activity log |
| **Server Scanner** | Game & region dropdowns, scan button, results table with latency/loss/status |
| **DNS Optimizer** | Benchmark all DNS providers, shows avg/min/max/reliability in a table |
| **Ping Monitor** | Real-time latency graph, live stats (current/avg/min/max/jitter/loss/spikes/stability), start/stop |
| **Route Analyzer** | Traceroute with bottleneck detection, MTU discovery, quality rating |
| **System Optimizer** | Per-tweak apply/revert buttons, apply-all/revert-all, export scripts |
| **Socket Tuning** | View current settings, browse game-specific profiles with details |

### GUI Requirements

```bash
pip install customtkinter
```

Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for a modern, polished dark-mode experience. Requires Python 3.8+.

- **Windows**: Works out of the box
- **macOS**: Works (install `python-tk` if needed: `brew install python-tk`)
- **Linux**: May need `sudo apt install python3-tk` for the tkinter backend

## CLI Mode

### Interactive Menu
```bash
python3 main.py
```
This launches the full interactive terminal menu with all features.

### What Each Option Does

1. **Full Game Optimization** — Runs all optimizations automatically:
   - Scans servers → finds fastest
   - Benchmarks DNS → finds best resolver
   - Analyzes route → detects bottlenecks
   - Finds optimal MTU
   - Tunes socket settings
   - Optionally applies OS-level optimizations

2. **Scan & Test Game Servers** — Tests all servers for your game/region and shows latency, packet loss, and jitter.

3. **DNS Optimizer** — Tests Cloudflare, Google, Quad9, OpenDNS, AdGuard, NextDNS, and more. Shows which is fastest for you.

4. **Route Analyzer** — Full traceroute with:
   - Bottleneck detection (finds the slow hop)
   - Multi-path testing (port 80 + 443)
   - Optimal MTU discovery

5. **Real-time Ping Monitor** — Live latency display with:
   - Jitter calculation
   - Spike detection
   - Stability score (0-100)
   - ASCII latency graph

6. **System Network Optimizer** — OS-specific optimizations:

   | macOS | Linux | Windows |
   |-------|-------|---------|
   | Disable delayed ACK | Enable BBR congestion | Disable Nagle's |
   | TCP Fast Open | TCP Fast Open | Disable network throttling |
   | Increase buffers | Low latency mode | Gaming priority |
   | Disable Wi-Fi power save | Disable SACK | Disable chimney offload |
   | Reduce keepalive | Optimize buffers | Flush DNS |

7. **TCP/UDP Socket Tuning** — Pre-configured profiles:
   - **Competitive FPS**: Ultra-low send latency (256KB buffers)
   - **Battle Royale**: Balanced for large world updates (1MB recv)
   - **MOBA**: Optimized for frequent small packets
   - **Ultra Low Latency**: Minimum possible delay (128KB buffers)

8. **Network Diagnostics** — Tests connectivity to major game infrastructure.

9. **Generate Scripts** — Creates shell/batch scripts to apply and revert optimizations.

0. **Revert All** — Undoes all system-level changes.

## Requirements

- **Python 3.8+** (uses asyncio)
- No external packages required
- `sudo` access for system optimizations (optional)

## How It Works

### TCP Ping (No Root Required)
Uses TCP SYN→SYN-ACK handshake timing to measure latency. Works without root/admin privileges — no raw sockets needed.

### ICMP Ping (Root Required)
Falls back to sending raw ICMP echo requests when root access is available.

### System Optimizations
Applies kernel-level network tuning via:
- `sysctl` on macOS/Linux
- `netsh` and registry on Windows

All changes are reversible with the built-in revert feature.

## Project Structure

```
exitlag/
├── main.py              # CLI application & interactive menu
├── config.py            # Configuration, game servers, DNS servers
├── network_scanner.py   # ICMP/TCP ping, multi-ping, jitter measurement
├── route_optimizer.py   # Traceroute, route analysis, MTU optimization
├── dns_optimizer.py     # DNS benchmarking and optimization
├── tcp_udp_tuner.py     # Socket profiles and TCP/UDP tuning
├── ping_monitor.py      # Real-time monitoring with statistics
├── os_optimizer.py      # OS-level network optimizations
├── requirements.txt     # Dependencies (customtkinter for GUI)
└── README.md            # This file
```

## License

Free and open source. Use it, modify it, share it.
