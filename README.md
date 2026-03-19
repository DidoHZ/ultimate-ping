# UltimatePing — Ultimate Gaming Network Optimizer

**Better than ExitLag — Free, Open Source, No Subscription**

A Python-based network optimization tool that reduces ping and improves connection quality for online gaming. Features an **AI-powered intelligence engine** that learns from your network history and adapts optimizations in real time. Works on **macOS, Linux, and Windows**.

---

## Features

| Feature | Description |
|---------|-------------|
| **Smart Mode (AI)** | Auto-detects running games, region, and network quality — picks the optimal server and settings automatically |
| **Intelligence Engine** | Learns from scan/DNS/route/monitor history to improve recommendations over time |
| **Full Game Optimization** | One-click optimization for popular games (Valorant, CS2, LoL, Fortnite, etc.) |
| **Server Scanner** | Adaptive scanning — tests all game servers with strategy tuned to your network condition |
| **DNS Optimizer** | Intelligent benchmark of 8+ DNS providers with reliability weighting from past results |
| **Route Analyzer** | Traceroute with bottleneck detection, multi-path analysis, and anomaly comparison |
| **Real-time Monitor** | Live ping monitoring with jitter, spike detection, stability scoring, and anomaly alerts |
| **System Optimizer** | OS-level TCP/UDP tuning with per-tweak apply/revert and intelligent auto-configuration |
| **Socket Tuning** | Game-specific socket profiles (FPS, MOBA, Battle Royale, MMO) plus AI-generated profiles |
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
# Install dependencies
pip install -r requirements.txt

# CLI mode (terminal)
python3 main.py

# GUI mode (graphical window)
python3 main.py --gui
# or directly:
python3 gui.py
```

## GUI

Modern dark-themed interface built with **CustomTkinter**, featuring professional SVG icons (via [pyconify](https://github.com/pyapp-kit/pyconify) + [Lucide](https://lucide.dev/)), sidebar navigation, real-time ping graphs, and slide-in toast notifications.

### Pages

| Page | Features |
|------|----------|
| **Dashboard** | Stats cards (ping/jitter/loss/stability), quick-action buttons, activity log |
| **Smart Mode** | AI-powered auto-detect for game/region/network, recommendations panel, intelligence log |
| **Server Scanner** | Game & region dropdowns, adaptive scan, results table with latency/loss/status |
| **DNS Optimizer** | Intelligent benchmark, avg/min/max/reliability table, best DNS card |
| **Ping Monitor** | Real-time latency graph, live stats, anomaly detection, start/stop toggle |
| **Route Analyzer** | Traceroute with bottleneck detection, MTU discovery, quality rating, recommendations |
| **System Optimizer** | Per-tweak apply/revert, intelligent auto-config, apply-all/revert-all, export scripts |
| **Socket Tuning** | Current settings view, game-specific profiles, AI-generated intelligent profiles |

### Requirements

```bash
pip install customtkinter pyconify cairosvg Pillow
```

- **macOS**: Requires Cairo (`brew install cairo`) and optionally `python-tk` (`brew install python-tk`)
- **Windows**: Works out of the box
- **Linux**: May need `sudo apt install python3-tk libcairo2`

> Icons degrade gracefully — if pyconify/cairosvg aren't installed, the GUI still works with dot fallbacks.

## Intelligence Engine

The intelligence module (`intelligence.py`) adds learning and adaptive behavior across every subsystem:

| Component | What It Does |
|-----------|-------------|
| **Game Detection** | Scans running processes to auto-identify games (supports 15+ titles) |
| **Region Detection** | Geo-locates via timezone/locale, falls back to latency-based measurement |
| **Network Assessment** | Evaluates base latency, jitter, and packet loss to classify network quality |
| **Performance History** | Persists scan results to disk — weights recent data for server ranking |
| **Ping Strategy** | Chooses ping method (TCP/ICMP), count, timeout, and parallelism based on conditions |
| **DNS History** | Tracks DNS benchmark results over time with reliability scoring |
| **Route History** | Records traceroute data and detects changes/regressions between runs |
| **Monitor Anomalies** | Learns baseline latency and alerts on spikes, jitter surges, and loss events |
| **Adaptive Sockets** | Generates socket profiles tuned to detected game + network condition |
| **Adaptive OS Config** | Recommends OS-level tweaks based on platform, network quality, and game type |
| **Smart Select** | Orchestrates all of the above into a single "run everything" analysis |

Data is persisted to `~/.ultimateping/` so the engine improves across sessions.

## CLI Mode

### Interactive Menu
```bash
python3 main.py
```
Launches the full interactive terminal menu with all features.

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
- **GUI dependencies**: `customtkinter`, `pyconify`, `cairosvg`, `Pillow`
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

## Building

### macOS (.app)
```bash
bash build_macos.sh
```

### Windows (.exe)
```batch
build_windows.bat
```

Both use PyInstaller and include the app icon.

## Project Structure

```
exitlag/
├── main.py              # CLI application & interactive menu
├── gui.py               # CustomTkinter GUI (dark theme, SVG icons)
├── intelligence.py      # AI intelligence engine (learning, adaptive strategies)
├── config.py            # Configuration, game servers, DNS servers
├── network_scanner.py   # ICMP/TCP ping, multi-ping, jitter measurement
├── route_optimizer.py   # Traceroute, route analysis, MTU optimization
├── dns_optimizer.py     # DNS benchmarking and optimization
├── tcp_udp_tuner.py     # Socket profiles and TCP/UDP tuning
├── ping_monitor.py      # Real-time monitoring with statistics
├── os_optimizer.py      # OS-level network optimizations
├── gen_icon.py          # Icon generation utility
├── build_macos.sh       # macOS build script (PyInstaller)
├── build_windows.bat    # Windows build script (PyInstaller)
├── ultimateping.spec    # PyInstaller spec file
├── requirements.txt     # Dependencies
└── README.md            # This file
```

## License

Free and open source. Use it, modify it, share it.
