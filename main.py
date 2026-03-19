"""
UltimatePing - Ultimate Gaming Network Optimizer
Main CLI application with interactive menu system.
"""

import asyncio
import os
import platform
import sys
import time
from typing import List, Optional

from config import GAME_SERVERS, OptimizationConfig
from network_scanner import (
    PingResult,
    get_network_info,
    measure_jitter,
    multi_ping,
    scan_servers,
)
from route_optimizer import (
    analyze_route,
    compare_routes,
    find_optimal_mtu,
    multi_path_test,
)
from dns_optimizer import (
    benchmark_all_dns,
    get_best_dns,
    get_current_dns,
)
from tcp_udp_tuner import (
    GAMING_PROFILES,
    get_current_socket_settings,
    get_profile_for_game,
    get_intelligent_profile,
    generate_optimization_report,
)
from ping_monitor import PingMonitor
from os_optimizer import (
    apply_all_optimizations,
    apply_intelligent_optimizations,
    generate_optimization_script,
    generate_revert_script,
    get_optimizations,
    read_current_values,
    revert_all_optimizations,
)
from intelligence import (
    detect_region,
    detect_region_by_latency,
    detect_running_games,
    assess_network,
    PerformanceHistory,
    choose_ping_strategy,
    generate_recommendations,
    smart_select,
    intelligent_dns_select,
    intelligent_route_analyze,
    intelligent_socket_config,
    intelligent_os_config,
    choose_monitor_strategy,
    choose_dns_strategy,
    choose_route_strategy,
    adaptive_scan_config,
    full_intelligent_optimize,
    DNSHistory,
    RouteHistory,
    IntelligentMonitor,
)


# ─── Terminal Colors ─────────────────────────────────────────────────────────

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_BLUE = "\033[44m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"


def clear_screen():
    os.system("cls" if platform.system() == "Windows" else "clear")


def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
    ██╗   ██╗██╗  ████████╗██╗███╗   ███╗ █████╗ ████████╗███████╗
    ██║   ██║██║  ╚══██╔══╝██║████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
    ██║   ██║██║     ██║   ██║██╔████╔██║███████║   ██║   █████╗
    ██║   ██║██║     ██║   ██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝
    ╚██████╔╝███████╗██║   ██║██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
     ╚═════╝ ╚══════╝╚═╝   ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
    {Colors.YELLOW}██████╗ ██╗███╗   ██╗ ██████╗
    ██╔══██╗██║████╗  ██║██╔════╝
    ██████╔╝██║██╔██╗ ██║██║  ███╗
    ██╔═══╝ ██║██║╚██╗██║██║   ██║
    ██║     ██║██║ ╚████║╚██████╔╝
    ╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝ {Colors.RESET}

    {Colors.DIM}Ultimate Gaming Network Optimizer{Colors.RESET}
    {Colors.DIM}Better than ExitLag — Free & Open Source{Colors.RESET}
    {Colors.DIM}OS: {platform.system()} {platform.release()}{Colors.RESET}
"""
    print(banner)


def print_header(title: str):
    width = 60
    print(f"\n{Colors.CYAN}{'═' * width}")
    print(f"  {Colors.BOLD}{title}{Colors.RESET}")
    print(f"{Colors.CYAN}{'═' * width}{Colors.RESET}\n")


def print_success(msg: str):
    print(f"  {Colors.GREEN}✓{Colors.RESET} {msg}")


def print_error(msg: str):
    print(f"  {Colors.RED}✗{Colors.RESET} {msg}")


def print_info(msg: str):
    print(f"  {Colors.BLUE}ℹ{Colors.RESET} {msg}")


def print_warning(msg: str):
    print(f"  {Colors.YELLOW}⚠{Colors.RESET} {msg}")


def latency_color(ms: float) -> str:
    if ms < 0:
        return Colors.RED
    elif ms < 30:
        return Colors.GREEN
    elif ms < 60:
        return Colors.YELLOW
    elif ms < 100:
        return Colors.YELLOW
    return Colors.RED


# ─── Menu Functions ──────────────────────────────────────────────────────────

def show_main_menu() -> str:
    print(f"""
{Colors.BOLD}  ┌─ MAIN MENU ─────────────────────────────────────┐{Colors.RESET}
  │                                                  │
  │  {Colors.CYAN}1.{Colors.RESET}  🎮  Full Game Optimization (Auto)          │
  │  {Colors.CYAN}2.{Colors.RESET}  📡  Scan & Test Game Servers              │
  │  {Colors.CYAN}3.{Colors.RESET}  🌐  DNS Optimizer                         │
  │  {Colors.CYAN}4.{Colors.RESET}  🛤️   Route Analyzer                        │
  │  {Colors.CYAN}5.{Colors.RESET}  📊  Real-time Ping Monitor                │
  │  {Colors.CYAN}6.{Colors.RESET}  ⚙️   System Network Optimizer              │
  │  {Colors.CYAN}7.{Colors.RESET}  🔧  TCP/UDP Socket Tuning                 │
  │  {Colors.CYAN}8.{Colors.RESET}  📋  Network Diagnostics                   │
  │  {Colors.CYAN}9.{Colors.RESET}  📝  Generate Optimization Scripts         │
  │  {Colors.CYAN}0.{Colors.RESET}  ↩️   Revert All Changes                    │
  │                                                  │
  │  {Colors.MAGENTA}s.{Colors.RESET}  🧠  Smart Mode (Intelligent)              │
  │  {Colors.DIM}q.  Exit{Colors.RESET}                                       │
  │                                                  │
  └──────────────────────────────────────────────────┘
""")
    return input(f"  {Colors.CYAN}>{Colors.RESET} Select option: ").strip()


def select_game() -> Optional[str]:
    games = list(GAME_SERVERS.keys())
    print(f"\n{Colors.BOLD}  Available Games:{Colors.RESET}\n")
    for i, game in enumerate(games, 1):
        name = game.replace("_", " ").title()
        if game == "custom":
            name = "Custom Server (Enter IP/hostname)"
        print(f"    {Colors.CYAN}{i}.{Colors.RESET} {name}")

    choice = input(f"\n  {Colors.CYAN}>{Colors.RESET} Select game: ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(games):
            return games[idx]
    except ValueError:
        pass
    return None


def select_region(game: str) -> Optional[str]:
    regions = list(GAME_SERVERS.get(game, {}).keys())
    if not regions:
        return None

    print(f"\n{Colors.BOLD}  Available Regions:{Colors.RESET}\n")
    for i, region in enumerate(regions, 1):
        print(f"    {Colors.CYAN}{i}.{Colors.RESET} {region}")
    print(f"    {Colors.CYAN}a.{Colors.RESET} Test ALL regions")

    choice = input(f"\n  {Colors.CYAN}>{Colors.RESET} Select region: ").strip()
    if choice.lower() == "a":
        return "ALL"
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(regions):
            return regions[idx]
    except ValueError:
        pass
    return None


def get_servers_for_selection(game: str, region: str) -> List[str]:
    """Get server list based on game and region selection."""
    if region == "ALL":
        servers = []
        for r_servers in GAME_SERVERS.get(game, {}).values():
            servers.extend(r_servers)
        return servers
    return GAME_SERVERS.get(game, {}).get(region, [])


# ─── Feature Implementations ────────────────────────────────────────────────

async def full_optimization():
    """Run full intelligent optimization pipeline for a game."""
    clear_screen()
    print_header("🧠 FULL GAME OPTIMIZATION (INTELLIGENT)")

    game = select_game()
    if not game:
        print_error("Invalid game selection.")
        return

    if game == "custom":
        server = input(f"  {Colors.CYAN}>{Colors.RESET} Enter server IP/hostname: ").strip()
        if not server:
            print_error("No server specified.")
            return
        servers = [server]
        game_name = "Custom"
    else:
        region = select_region(game)
        if not region:
            print_error("Invalid region selection.")
            return
        servers = get_servers_for_selection(game, region)
        game_name = game.replace("_", " ").title()

    config = OptimizationConfig.load()
    config.selected_game = game
    config.save()

    print(f"\n{Colors.BOLD}  Optimizing for: {Colors.CYAN}{game_name}{Colors.RESET}\n")

    # Step 0: Assess network condition (drives all other decisions)
    print(f"  {Colors.YELLOW}[0/6]{Colors.RESET} Assessing network condition…")
    cond = await assess_network()
    qcolors = {"excellent": Colors.GREEN, "good": Colors.GREEN, "fair": Colors.YELLOW, "poor": Colors.RED, "bad": Colors.RED}
    qc = qcolors.get(cond.quality, Colors.WHITE)
    print_success(f"Network: {qc}{cond.quality.upper()}{Colors.RESET} — "
                  f"latency {cond.base_latency_ms}ms, jitter {cond.jitter_ms}ms, loss {cond.loss_pct}%")

    # Step 1: Smart server scan (adaptive parameters)
    print(f"\n  {Colors.YELLOW}[1/6]{Colors.RESET} Scanning servers (adaptive)…")
    scan_config = adaptive_scan_config(cond, game)
    results = await scan_servers(servers, scan_config, use_tcp=True)

    if results and results[0].is_reachable:
        best = results[0]
        color = latency_color(best.latency_ms)
        hist = PerformanceHistory()
        hist_rec = hist.get(best.host)
        hist_flag = f" {Colors.MAGENTA}(★ history-informed){Colors.RESET}" if hist_rec and hist_rec.samples >= 3 else ""
        print_success(f"Best server: {best.host} ({color}{best.latency_ms}ms{Colors.RESET}){hist_flag}")
        target = best.host
    else:
        print_warning("No servers reachable via TCP, using first server.")
        target = servers[0]

    # Step 2: Intelligent DNS optimization
    print(f"\n  {Colors.YELLOW}[2/6]{Colors.RESET} Intelligent DNS selection…")
    best_dns_rec, dns_recs = await intelligent_dns_select(game)
    if best_dns_rec:
        print_success(
            f"Best DNS: {best_dns_rec.provider} ({best_dns_rec.ip}) — "
            f"{best_dns_rec.avg_ms}ms, score {best_dns_rec.score}/100"
        )
        for r in dns_recs:
            if r.priority <= 3:
                print_info(f"💡 {r.title}: {r.detail}")
    else:
        print_warning("Could not determine best DNS.")

    # Step 3: Intelligent route analysis
    print(f"\n  {Colors.YELLOW}[3/6]{Colors.RESET} Intelligent route analysis…")
    route, route_recs = await intelligent_route_analyze(target, game)
    quality_colors = {
        "excellent": Colors.GREEN, "good": Colors.GREEN,
        "fair": Colors.YELLOW, "poor": Colors.RED
    }
    qcolor = quality_colors.get(route.route_quality, Colors.WHITE)
    print_success(f"Route quality: {qcolor}{route.route_quality.upper()}{Colors.RESET}")
    print_info(f"Hops: {route.total_hops} | Avg latency: {route.avg_latency}ms")
    if route.bottleneck_hop:
        print_warning(
            f"Bottleneck at hop {route.bottleneck_hop.hop_number}: "
            f"{route.bottleneck_hop.ip} ({route.bottleneck_hop.latency_ms}ms)"
        )
    for r in route_recs:
        if r.priority <= 2:
            print_warning(f"⚠ {r.title}: {r.detail}")

    # Step 4: MTU optimization
    print(f"\n  {Colors.YELLOW}[4/6]{Colors.RESET} Finding optimal MTU…")
    optimal_mtu = await find_optimal_mtu(target)
    print_success(f"Optimal MTU: {optimal_mtu}")

    # Step 5: Intelligent socket tuning
    print(f"\n  {Colors.YELLOW}[5/6]{Colors.RESET} Intelligent socket tuning…")
    socket_cfg, socket_recs = intelligent_socket_config(cond, game)
    profile = get_intelligent_profile(game if game != "custom" else None)
    current = get_current_socket_settings()
    changes = generate_optimization_report(profile, current)
    print_info(f"Strategy: {socket_cfg.reason}")
    for change in changes:
        print(f"    {change}")

    # Step 6: Intelligent OS optimization
    print(f"\n  {Colors.YELLOW}[6/6]{Colors.RESET} Intelligent OS optimization analysis…")
    os_cfg, os_recs = intelligent_os_config(cond, game)
    print_info(f"Strategy: {os_cfg.reason}")
    print_info(f"Recommended: {len(os_cfg.recommended_indices)} optimizations, skipping: {len(os_cfg.skip_indices)}")
    for r in os_recs:
        prio_c = Colors.RED if r.priority <= 2 else Colors.YELLOW if r.priority <= 3 else Colors.DIM
        print(f"    {prio_c}[P{r.priority}]{Colors.RESET} {r.title}")

    # Summary
    print(f"\n{Colors.BOLD}{'─' * 60}{Colors.RESET}")
    print(f"\n{Colors.GREEN}{Colors.BOLD}  🧠 INTELLIGENT OPTIMIZATION REPORT{Colors.RESET}\n")

    print(f"    Network:   {qc}{cond.quality.upper()}{Colors.RESET}")
    if results and results[0].is_reachable:
        color = latency_color(results[0].latency_ms)
        print(f"    Server:    {results[0].host}")
        print(f"    Ping:      {color}{results[0].latency_ms}ms{Colors.RESET}")
        print(f"    Loss:      {results[0].packet_loss}%")

    print(f"    Route:     {qcolor}{route.route_quality.upper()}{Colors.RESET} ({route.total_hops} hops)")
    print(f"    MTU:       {optimal_mtu}")
    print(f"    Profile:   {profile.name}")

    if best_dns_rec:
        print(f"    DNS:       {best_dns_rec.provider} ({best_dns_rec.avg_ms}ms, score {best_dns_rec.score}/100)")

    # Ask to apply intelligent system optimizations
    print(f"\n{Colors.YELLOW}  Apply intelligent system optimizations? (requires sudo){Colors.RESET}")
    print(f"  {Colors.DIM}({len(os_cfg.recommended_indices)} selected, {len(os_cfg.skip_indices)} skipped based on network condition){Colors.RESET}")
    choice = input(f"  {Colors.CYAN}>{Colors.RESET} [y/N]: ").strip().lower()
    if choice == "y":
        print(f"\n  Applying intelligent optimizations…")
        results_apply, skipped = apply_intelligent_optimizations(game)
        for ok, msg in results_apply:
            if ok:
                print_success(msg)
            else:
                print_error(msg)
        if skipped:
            print_info(f"Skipped ({len(skipped)}): {', '.join(skipped)}")

    print(f"\n{Colors.GREEN}  Intelligent optimization complete!{Colors.RESET}\n")
    input("  Press Enter to continue…")


async def scan_game_servers():
    """Scan and test game servers with intelligent adaptive parameters."""
    clear_screen()
    print_header("🧠 GAME SERVER SCANNER (INTELLIGENT)")

    game = select_game()
    if not game:
        print_error("Invalid game selection.")
        return

    if game == "custom":
        server_input = input(
            f"  {Colors.CYAN}>{Colors.RESET} Enter servers (comma-separated): "
        ).strip()
        servers = [s.strip() for s in server_input.split(",") if s.strip()]
    else:
        region = select_region(game)
        if not region:
            print_error("Invalid region selection.")
            return
        servers = get_servers_for_selection(game, region)

    if not servers:
        print_error("No servers to test.")
        return

    # Assess network condition for adaptive scan parameters
    print(f"\n  Assessing network condition…")
    cond = await assess_network()
    config = adaptive_scan_config(cond, game)
    qcolors = {"excellent": Colors.GREEN, "good": Colors.GREEN, "fair": Colors.YELLOW, "poor": Colors.RED, "bad": Colors.RED}
    qc = qcolors.get(cond.quality, Colors.WHITE)
    print_info(f"Network: {qc}{cond.quality.upper()}{Colors.RESET} — "
               f"adaptive scan: {config.ping_count} probes, {config.ping_interval}s interval")

    print(f"\n  Testing {len(servers)} server(s)…\n")
    results = await scan_servers(servers, config, use_tcp=True)

    # Display results with history info
    hist = PerformanceHistory()
    print(f"  {'Server':<40} {'IP':<18} {'Ping':<10} {'Loss':<8} {'Score':<8} {'Status':<10}")
    print(f"  {'─' * 40} {'─' * 18} {'─' * 10} {'─' * 8} {'─' * 8} {'─' * 10}")

    for r in results:
        color = latency_color(r.latency_ms) if r.is_reachable else Colors.RED
        status = f"{Colors.GREEN}ONLINE{Colors.RESET}" if r.is_reachable else f"{Colors.RED}OFFLINE{Colors.RESET}"
        ping_str = f"{color}{r.latency_ms}ms{Colors.RESET}" if r.is_reachable else f"{Colors.RED}---{Colors.RESET}"
        h = hist.get(r.host)
        score_str = f"{h.score}/100" if h and h.samples > 0 else "—"
        print(f"  {r.host:<40} {r.ip:<18} {ping_str:<20} {r.packet_loss}%    {score_str:<8} {status}")

    # Jitter test for best server
    if results and results[0].is_reachable:
        print(f"\n  Running jitter analysis for best server...")
        avg, min_l, max_l, jitter = await measure_jitter(results[0].host)
        if avg > 0:
            print(f"\n    Avg: {avg}ms | Min: {min_l}ms | Max: {max_l}ms | Jitter: {jitter}ms")

    print()
    input("  Press Enter to continue...")


async def dns_optimizer_menu():
    """Intelligent DNS optimization menu."""
    clear_screen()
    print_header("🧠 DNS OPTIMIZER (INTELLIGENT)")

    # Show current DNS
    current = get_current_dns()
    print(f"  Current DNS servers: {', '.join(current)}\n")

    # Assess network + choose DNS strategy
    print(f"  Assessing network condition…")
    cond = await assess_network()
    strategy = choose_dns_strategy(cond)
    qcolors = {"excellent": Colors.GREEN, "good": Colors.GREEN, "fair": Colors.YELLOW, "poor": Colors.RED, "bad": Colors.RED}
    qc = qcolors.get(cond.quality, Colors.WHITE)
    print_info(f"Network: {qc}{cond.quality.upper()}{Colors.RESET} — DNS strategy: {strategy.reason}")

    # Intelligent DNS selection (uses history + live benchmarks)
    game = OptimizationConfig.load().selected_game
    print(f"\n  Running intelligent DNS selection (history + live)…\n")
    best_rec, recs = await intelligent_dns_select(game)

    # Also run full benchmark for display
    config = OptimizationConfig.load()
    results = await benchmark_all_dns(config)

    # Display results with intelligence score
    print(f"  {'DNS Provider':<18} {'Primary IP':<18} {'Avg':<10} {'Min':<10} {'Max':<10} {'Reliability':<12} {'Score':<8}")
    print(f"  {'─' * 18} {'─' * 18} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 12} {'─' * 8}")

    for r in results:
        if r.resolved_correctly:
            color = latency_color(r.avg_latency_ms)
            score_str = f"{getattr(r, '_sort_key', 0):.0f}" if hasattr(r, '_sort_key') else "—"
            print(
                f"  {r.name:<18} {r.primary_ip:<18} "
                f"{color}{r.avg_latency_ms:>6.1f}ms{Colors.RESET}  "
                f"{r.min_latency_ms:>6.1f}ms  "
                f"{r.max_latency_ms:>6.1f}ms  "
                f"{Colors.GREEN}{r.reliability:>5.1f}%{Colors.RESET}  "
                f"{score_str:<8}"
            )
        else:
            print(f"  {r.name:<18} {r.primary_ip:<18} {Colors.RED}FAILED{Colors.RESET}")

    if best_rec:
        print(f"\n  {Colors.GREEN}🧠 Intelligent pick: {best_rec.provider} ({best_rec.ip}) — "
              f"{best_rec.avg_ms}ms, score {best_rec.score}/100{Colors.RESET}")
        for r in recs:
            if r.priority <= 3:
                prio_c = Colors.RED if r.priority <= 2 else Colors.YELLOW
                print(f"    {prio_c}[P{r.priority}]{Colors.RESET} {r.title}: {r.detail}")

    if results and results[0].resolved_correctly:
        best = results[0]
        print(f"\n  {Colors.DIM}To change DNS on macOS:{Colors.RESET}")
        print(f"    {Colors.DIM}networksetup -setdnsservers Wi-Fi {best.primary_ip} {best.secondary_ip}{Colors.RESET}")

    print()
    input("  Press Enter to continue…")


async def route_analyzer_menu():
    """Intelligent route analysis menu."""
    clear_screen()
    print_header("🧠 ROUTE ANALYZER (INTELLIGENT)")

    target = input(f"  {Colors.CYAN}>{Colors.RESET} Enter target (IP/hostname): ").strip()
    if not target:
        print_error("No target specified.")
        return

    # Assess network + choose route strategy
    print(f"\n  Assessing network condition…")
    cond = await assess_network()
    route_strat = choose_route_strategy(cond)
    qcolors = {"excellent": Colors.GREEN, "good": Colors.GREEN, "fair": Colors.YELLOW, "poor": Colors.RED, "bad": Colors.RED}
    qc = qcolors.get(cond.quality, Colors.WHITE)
    print_info(f"Network: {qc}{cond.quality.upper()}{Colors.RESET} — route strategy: {route_strat.reason}")

    # Intelligent route analysis (records history, compares with previous)
    game = OptimizationConfig.load().selected_game
    print(f"\n  Running intelligent route analysis…\n")
    route, recs = await intelligent_route_analyze(target, game)

    # Display route hops
    for hop in route.hops:
        if hop.is_reachable:
            color = latency_color(hop.latency_ms)
            is_bottleneck = (
                route.bottleneck_hop
                and hop.hop_number == route.bottleneck_hop.hop_number
            )
            marker = f" {Colors.RED}← BOTTLENECK{Colors.RESET}" if is_bottleneck else ""
            print(
                f"    {hop.hop_number:>3}  {hop.ip or '???':<18} "
                f"{color}{hop.latency_ms:>8.1f}ms{Colors.RESET}{marker}"
            )
        else:
            print(f"    {hop.hop_number:>3}  {'* * *':<18} {Colors.DIM}timeout{Colors.RESET}")

    quality_colors = {
        "excellent": Colors.GREEN, "good": Colors.GREEN,
        "fair": Colors.YELLOW, "poor": Colors.RED
    }
    qcolor = quality_colors.get(route.route_quality, Colors.WHITE)
    print(f"\n  Route Quality: {qcolor}{route.route_quality.upper()}{Colors.RESET}")
    print(f"  Total Hops: {route.total_hops}")
    print(f"  Avg Latency: {route.avg_latency}ms")

    # Intelligence recommendations
    if recs:
        print(f"\n  {Colors.BOLD}🧠 Intelligent analysis:{Colors.RESET}")
        for r in recs:
            prio_c = Colors.RED if r.priority <= 2 else Colors.YELLOW if r.priority <= 3 else Colors.DIM
            print(f"    {prio_c}[P{r.priority}]{Colors.RESET} {r.title}: {r.detail}")

    # Route history summary
    route_hist = RouteHistory()
    hist_rec = route_hist.get(target)
    if hist_rec and hist_rec.samples > 1:
        print(f"\n  {Colors.MAGENTA}★ Route history ({hist_rec.samples} samples):{Colors.RESET}")
        print(f"    Avg hops: {hist_rec.avg_hops:.1f} | Avg latency: {hist_rec.avg_latency:.1f}ms")
        if hist_rec.known_bottleneck_ips:
            print(f"    Known bottlenecks: {', '.join(hist_rec.known_bottleneck_ips)}")

    # Multi-path test
    print(f"\n  Running multi-path test…")
    best, avg, worst = await multi_path_test(target)
    if best > 0:
        print(f"    Best: {best}ms | Avg: {avg}ms | Worst: {worst}ms")

    # MTU test
    print(f"\n  Finding optimal MTU…")
    mtu = await find_optimal_mtu(target)
    print(f"    Optimal MTU: {mtu}")

    print()
    input("  Press Enter to continue…")


async def ping_monitor_menu():
    """Intelligent real-time ping monitor with anomaly detection."""
    clear_screen()
    print_header("🧠 REAL-TIME PING MONITOR (INTELLIGENT)")

    target = input(f"  {Colors.CYAN}>{Colors.RESET} Enter target (IP/hostname): ").strip()
    if not target:
        target = "8.8.8.8"

    port_str = input(f"  {Colors.CYAN}>{Colors.RESET} Port (default 80): ").strip()
    try:
        port = int(port_str) if port_str else 80
    except ValueError:
        port = 80

    # Assess network to choose monitoring strategy
    print(f"\n  Assessing network…")
    cond = await assess_network()
    mon_strat = choose_monitor_strategy(cond)
    qcolors = {"excellent": Colors.GREEN, "good": Colors.GREEN, "fair": Colors.YELLOW, "poor": Colors.RED, "bad": Colors.RED}
    qc = qcolors.get(cond.quality, Colors.WHITE)
    print_info(f"Network: {qc}{cond.quality.upper()}{Colors.RESET} — "
               f"monitor: interval={mon_strat.interval}s, spike_threshold={mon_strat.spike_threshold}ms")

    print(f"\n  Monitoring {target}:{port} — Press Ctrl+C to stop\n")

    monitor = PingMonitor(target, port=port, interval=mon_strat.interval, history_size=200)

    anomaly_alerts = []

    def on_update(snapshot, stats):
        anomaly_marker = ""
        if hasattr(monitor, '_intel_monitor'):
            summary = monitor.get_anomaly_summary()
            total_a = sum(summary.values())
            if total_a > len(anomaly_alerts):
                anomaly_marker = f" {Colors.RED}⚠ ANOMALY{Colors.RESET}"

        if snapshot.is_timeout:
            sys.stdout.write(f"\r  {Colors.RED}TIMEOUT{Colors.RESET}  | "
                           f"Avg: {stats.avg_ms:.1f}ms | "
                           f"Jitter: {stats.jitter_ms:.1f}ms | "
                           f"Loss: {stats.packet_loss_pct}% | "
                           f"Score: {stats.stability_score}/100{anomaly_marker}  ")
        else:
            color = latency_color(snapshot.latency_ms)
            sys.stdout.write(f"\r  {color}{snapshot.latency_ms:>6.1f}ms{Colors.RESET} | "
                           f"Avg: {stats.avg_ms:.1f}ms | "
                           f"Min: {stats.min_ms:.1f}ms | "
                           f"Max: {stats.max_ms:.1f}ms | "
                           f"Jitter: {stats.jitter_ms:.1f}ms | "
                           f"Loss: {stats.packet_loss_pct}% | "
                           f"Score: {stats.stability_score}/100{anomaly_marker}  ")
        sys.stdout.flush()

    monitor.on_update(on_update)

    try:
        await monitor.start()
    except (KeyboardInterrupt, asyncio.CancelledError):
        monitor.stop()
        print("\n")
        print(monitor.get_summary())
        print(monitor.get_latency_graph())

        # Show intelligent anomaly analysis
        if hasattr(monitor, '_intel_monitor'):
            summary = monitor.get_anomaly_summary()
            if any(v > 0 for v in summary.values()):
                print(f"\n  {Colors.BOLD}🧠 Anomaly Analysis:{Colors.RESET}")
                for kind, count in summary.items():
                    if count > 0:
                        print(f"    {Colors.YELLOW}{kind}{Colors.RESET}: {count} occurrences")

                recs = monitor.get_anomaly_recommendations()
                if recs:
                    print(f"\n  {Colors.BOLD}Recommendations:{Colors.RESET}")
                    for r in recs:
                        prio_c = Colors.RED if r.priority <= 2 else Colors.YELLOW if r.priority <= 3 else Colors.DIM
                        print(f"    {prio_c}[P{r.priority}]{Colors.RESET} {r.title}: {r.detail}")

    print()
    input("  Press Enter to continue…")


async def system_optimizer_menu():
    """Intelligent system-level network optimization menu."""
    clear_screen()
    print_header("🧠 SYSTEM NETWORK OPTIMIZER (INTELLIGENT)")

    opts = get_optimizations()
    opts = read_current_values(opts)

    print(f"  {Colors.BOLD}Available Optimizations ({platform.system()}):{Colors.RESET}\n")

    for i, opt in enumerate(opts, 1):
        admin = f"{Colors.YELLOW}[sudo]{Colors.RESET}" if opt.requires_admin else ""
        current = f" (current: {opt.current_value})" if opt.current_value else ""
        print(f"    {Colors.CYAN}{i:>2}.{Colors.RESET} {opt.name} {admin}")
        print(f"        {Colors.DIM}{opt.description}{current}{Colors.RESET}")

    print(f"\n  Options:")
    print(f"    {Colors.CYAN}a{Colors.RESET} - Apply ALL optimizations")
    print(f"    {Colors.MAGENTA}i{Colors.RESET} - 🧠 Intelligent (auto-select based on network condition)")
    print(f"    {Colors.CYAN}r{Colors.RESET} - Revert ALL optimizations")
    print(f"    {Colors.CYAN}#number{Colors.RESET} - Apply specific optimization")
    print(f"    {Colors.CYAN}q{Colors.RESET} - Back to menu")

    choice = input(f"\n  {Colors.CYAN}>{Colors.RESET} Choice: ").strip().lower()

    if choice == "i":
        # Intelligent mode: assess network and selectively apply
        print(f"\n  {Colors.MAGENTA}🧠 Assessing network condition…{Colors.RESET}")
        game = OptimizationConfig.load().selected_game
        cond = await assess_network()
        os_cfg, os_recs = intelligent_os_config(cond, game)
        qcolors = {"excellent": Colors.GREEN, "good": Colors.GREEN, "fair": Colors.YELLOW, "poor": Colors.RED, "bad": Colors.RED}
        qc = qcolors.get(cond.quality, Colors.WHITE)
        print_info(f"Network: {qc}{cond.quality.upper()}{Colors.RESET} — {os_cfg.reason}")
        print_info(f"Recommending {len(os_cfg.recommended_indices)} of {len(opts)} optimizations\n")

        for r in os_recs:
            prio_c = Colors.RED if r.priority <= 2 else Colors.YELLOW if r.priority <= 3 else Colors.DIM
            print(f"    {prio_c}[P{r.priority}]{Colors.RESET} {r.title}: {r.detail}")

        confirm = input(f"\n  {Colors.CYAN}>{Colors.RESET} Apply intelligent selection? [y/N]: ").strip().lower()
        if confirm == "y":
            results_apply, skipped = apply_intelligent_optimizations(game)
            for ok, msg in results_apply:
                if ok:
                    print_success(msg)
                else:
                    print_error(msg)
            if skipped:
                print_info(f"Skipped ({len(skipped)}): {', '.join(skipped)}")
    elif choice == "a":
        print(f"\n  {Colors.YELLOW}Applying all optimizations (requires sudo)…{Colors.RESET}\n")
        results = apply_all_optimizations()
        for ok, msg in results:
            if ok:
                print_success(msg)
            else:
                print_error(msg)
    elif choice == "r":
        print(f"\n  Reverting all optimizations…\n")
        results = revert_all_optimizations()
        for ok, msg in results:
            if ok:
                print_success(msg)
            else:
                print_error(msg)
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(opts):
            from os_optimizer import apply_optimization
            ok, msg = apply_optimization(opts[idx])
            if ok:
                print_success(msg)
            else:
                print_error(msg)

    print()
    input("  Press Enter to continue…")


async def tcp_udp_menu():
    """Intelligent TCP/UDP tuning menu."""
    clear_screen()
    print_header("🧠 TCP/UDP SOCKET TUNING (INTELLIGENT)")

    current = get_current_socket_settings()

    print(f"  {Colors.BOLD}Current Socket Settings:{Colors.RESET}\n")
    for key, value in current.items():
        print(f"    {key:<25} = {value:>12,}")

    print(f"\n  {Colors.BOLD}Gaming Profiles:{Colors.RESET}\n")
    for i, (key, profile) in enumerate(GAMING_PROFILES.items(), 1):
        print(f"    {Colors.CYAN}{i}.{Colors.RESET} {profile.name}")
        print(f"       {Colors.DIM}{profile.description}{Colors.RESET}")
        print(f"       TCP_NODELAY={profile.tcp_nodelay} | "
              f"Recv={profile.recv_buffer:,} | Send={profile.send_buffer:,}")
        print()

    print(f"    {Colors.MAGENTA}i.{Colors.RESET} 🧠 Intelligent (auto-tune based on network + game)")

    choice = input(f"\n  {Colors.CYAN}>{Colors.RESET} Select profile (or Enter to skip): ").strip()

    if choice.lower() == "i":
        # Intelligent profile
        game = OptimizationConfig.load().selected_game
        print(f"\n  {Colors.MAGENTA}🧠 Generating intelligent socket profile…{Colors.RESET}")
        profile = get_intelligent_profile(game)
        print_info(f"Profile: {profile.name}")
        print_info(f"{profile.description}")
        changes = generate_optimization_report(profile, current)
        print(f"\n  Recommended changes:")
        for change in changes:
            print(f"    {change}")
    elif choice.isdigit():
        idx = int(choice) - 1
        profiles = list(GAMING_PROFILES.values())
        if 0 <= idx < len(profiles):
            profile = profiles[idx]
            changes = generate_optimization_report(profile, current)
            print(f"\n  Changes for {profile.name}:")
            for change in changes:
                print(f"    {change}")

    print()
    input("  Press Enter to continue…")


async def network_diagnostics():
    """Run intelligent network diagnostics."""
    clear_screen()
    print_header("🧠 NETWORK DIAGNOSTICS (INTELLIGENT)")

    # Network info
    info = get_network_info()
    print(f"  {Colors.BOLD}Network Information:{Colors.RESET}")
    print(f"    Local IP:   {info.local_ip}")
    print(f"    Interface:  {info.interface}")
    print(f"    DNS:        {', '.join(get_current_dns())}")

    # Intelligent assessment
    print(f"\n  {Colors.BOLD}🧠 Network Assessment:{Colors.RESET}\n")
    cond = await assess_network()
    qcolors = {"excellent": Colors.GREEN, "good": Colors.GREEN, "fair": Colors.YELLOW, "poor": Colors.RED, "bad": Colors.RED}
    qc = qcolors.get(cond.quality, Colors.WHITE)
    print(f"    Quality:    {qc}{cond.quality.upper()}{Colors.RESET}")
    print(f"    Latency:    {cond.base_latency_ms}ms")
    print(f"    Jitter:     {cond.jitter_ms}ms")
    print(f"    Loss:       {cond.loss_pct}%")

    # Adaptive connectivity test
    scan_cfg = adaptive_scan_config(cond, None)
    print(f"\n  {Colors.BOLD}Connectivity Test (adaptive: {scan_cfg.ping_count} probes):{Colors.RESET}\n")

    test_targets = [
        ("Google DNS", "8.8.8.8"),
        ("Cloudflare DNS", "1.1.1.1"),
        ("Amazon AWS", "dynamodb.us-east-1.amazonaws.com"),
        ("Riot Games", "riot.com"),
        ("Epic Games", "epicgames.com"),
        ("Valve (Steam)", "store.steampowered.com"),
    ]

    for name, host in test_targets:
        result = await multi_ping(host, count=scan_cfg.ping_count,
                                  interval=scan_cfg.ping_interval,
                                  timeout=scan_cfg.timeout, use_tcp=True)
        if result.is_reachable:
            color = latency_color(result.latency_ms)
            print(f"    {Colors.GREEN}✓{Colors.RESET} {name:<25} {color}{result.latency_ms:>6.1f}ms{Colors.RESET}  loss: {result.packet_loss}%")
        else:
            print(f"    {Colors.RED}✗{Colors.RESET} {name:<25} {Colors.RED}UNREACHABLE{Colors.RESET}")

    # Socket settings
    print(f"\n  {Colors.BOLD}Socket Settings:{Colors.RESET}")
    settings = get_current_socket_settings()
    for key, val in settings.items():
        print(f"    {key:<25} = {val:>10,}")

    # Generate recommendations based on diagnostics
    recs = generate_recommendations(cond, None, [])
    if recs:
        print(f"\n  {Colors.BOLD}🧠 Recommendations:{Colors.RESET}")
        for r in recs:
            prio_c = Colors.RED if r.priority <= 2 else Colors.YELLOW if r.priority <= 3 else Colors.DIM
            print(f"    {prio_c}[P{r.priority}]{Colors.RESET} {r.title}: {r.detail}")

    print()
    input("  Press Enter to continue…")


async def generate_scripts():
    """Generate optimization and revert scripts."""
    clear_screen()
    print_header("GENERATE SCRIPTS")

    config = OptimizationConfig.load()
    config.config_dir.mkdir(parents=True, exist_ok=True)

    system = platform.system().lower()
    ext = ".bat" if system == "windows" else ".sh"

    # Generate optimization script
    opt_script = generate_optimization_script()
    opt_path = config.config_dir / f"optimize{ext}"
    opt_path.write_text(opt_script)
    if system != "windows":
        opt_path.chmod(0o755)

    # Generate revert script
    rev_script = generate_revert_script()
    rev_path = config.config_dir / f"revert{ext}"
    rev_path.write_text(rev_script)
    if system != "windows":
        rev_path.chmod(0o755)

    print_success(f"Optimization script: {opt_path}")
    print_success(f"Revert script: {rev_path}")

    print(f"\n  {Colors.DIM}Run with: sudo {opt_path}{Colors.RESET}")

    print()
    input("  Press Enter to continue...")


async def revert_changes():
    """Revert all optimizations."""
    clear_screen()
    print_header("REVERT ALL CHANGES")

    print(f"  {Colors.YELLOW}This will revert all system network optimizations.{Colors.RESET}\n")
    choice = input(f"  {Colors.CYAN}>{Colors.RESET} Continue? [y/N]: ").strip().lower()

    if choice == "y":
        results = revert_all_optimizations()
        for ok, msg in results:
            if ok:
                print_success(msg)
            else:
                print_error(msg)
        print(f"\n  {Colors.GREEN}All changes reverted.{Colors.RESET}")
    else:
        print_info("Cancelled.")

    print()
    input("  Press Enter to continue...")


async def smart_mode():
    """🧠 Intelligent mode — auto-detect everything and optimize."""
    clear_screen()
    print_header("🧠 SMART MODE — INTELLIGENT OPTIMIZER")

    # 1 — detect running games
    print(f"  {Colors.YELLOW}[1/6]{Colors.RESET} Scanning for running games…")
    detected = detect_running_games()
    game = None
    if detected:
        g = detected[0]
        print_success(f"Detected: {g.display_name} (PID {g.pid})")
        game = g.name
    else:
        print_info("No game detected — select manually or press Enter to skip.")
        games = list(GAME_SERVERS.keys())
        for i, gk in enumerate(games, 1):
            print(f"    {Colors.CYAN}{i}.{Colors.RESET} {gk.replace('_', ' ').title()}")
        ch = input(f"\n  {Colors.CYAN}>{Colors.RESET} Game (Enter to skip): ").strip()
        if ch.isdigit() and 1 <= int(ch) <= len(games):
            game = games[int(ch) - 1]

    # 2 — detect region
    print(f"\n  {Colors.YELLOW}[2/6]{Colors.RESET} Detecting your region…")
    geo = detect_region()
    if geo.confidence >= 0.6:
        print_success(f"Region: {geo.region_code} (via timezone: {geo.timezone}, {geo.confidence:.0%} confidence)")
        region = geo.region_code
    else:
        print_warning(f"Low-confidence region ({geo.region_code} @ {geo.confidence:.0%})")
        print_info("Running latency-based detection…")
        region = await detect_region_by_latency()
        print_success(f"Region by latency: {region}")

    # 3 — assess network
    print(f"\n  {Colors.YELLOW}[3/6]{Colors.RESET} Assessing network condition…")
    cond = await assess_network()
    qcolors = {"excellent": Colors.GREEN, "good": Colors.GREEN, "fair": Colors.YELLOW, "poor": Colors.RED, "bad": Colors.RED}
    qc = qcolors.get(cond.quality, Colors.WHITE)
    print_success(f"Quality: {qc}{cond.quality.upper()}{Colors.RESET} — "
                  f"latency {cond.base_latency_ms}ms, jitter {cond.jitter_ms}ms, loss {cond.loss_pct}%")

    # 4 — adaptive strategy
    print(f"\n  {Colors.YELLOW}[4/6]{Colors.RESET} Choosing ping strategy…")
    strat = choose_ping_strategy(cond, game)
    print_info(f"{strat.reason}")
    print_info(f"Probes: {strat.count} | Interval: {strat.interval}s | Timeout: {strat.timeout}s")

    # 5 — smart server selection
    print(f"\n  {Colors.YELLOW}[5/6]{Colors.RESET} Finding best server (history + live)…")
    result = await smart_select(game, region)

    if result.best_server:
        color = latency_color(result.best_latency)
        hist_flag = f" {Colors.MAGENTA}(★ history-informed){Colors.RESET}" if result.history_informed else ""
        print_success(f"Best: {result.best_server} — {color}{result.best_latency}ms{Colors.RESET}{hist_flag}")
    else:
        print_warning("No reachable server found.")

    # 6 — recommendations
    print(f"\n  {Colors.YELLOW}[6/6]{Colors.RESET} Generating recommendations…")
    recs = result.recommendations
    if recs:
        for r in recs:
            prio_c = Colors.RED if r.priority <= 2 else Colors.YELLOW if r.priority <= 3 else Colors.DIM
            print(f"    {prio_c}[P{r.priority}]{Colors.RESET} {Colors.BOLD}{r.title}{Colors.RESET}")
            print(f"         {Colors.DIM}{r.detail}{Colors.RESET}")
    else:
        print_success("Everything looks great — no urgent recommendations.")

    # summary card
    print(f"\n{Colors.BOLD}{'─' * 60}{Colors.RESET}")
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}  🧠 SMART MODE REPORT{Colors.RESET}\n")
    if game:
        print(f"    Game:       {game.replace('_', ' ').title()}")
    print(f"    Region:     {region}")
    print(f"    Network:    {qc}{cond.quality.upper()}{Colors.RESET}")
    if result.best_server:
        print(f"    Server:     {result.best_server}")
        print(f"    Latency:    {latency_color(result.best_latency)}{result.best_latency}ms{Colors.RESET}")
    print(f"    Strategy:   {strat.count} probes @ {strat.interval}s")
    print(f"    Tips:       {len(recs)} recommendations")

    print(f"\n{Colors.GREEN}  Smart optimization complete!{Colors.RESET}\n")
    input("  Press Enter to continue…")


# ─── Main Loop ───────────────────────────────────────────────────────────────

async def main():
    """Main application loop."""
    while True:
        clear_screen()
        print_banner()
        choice = show_main_menu()

        if choice == "1":
            await full_optimization()
        elif choice == "2":
            await scan_game_servers()
        elif choice == "3":
            await dns_optimizer_menu()
        elif choice == "4":
            await route_analyzer_menu()
        elif choice == "5":
            await ping_monitor_menu()
        elif choice == "6":
            await system_optimizer_menu()
        elif choice == "7":
            await tcp_udp_menu()
        elif choice == "8":
            await network_diagnostics()
        elif choice == "9":
            await generate_scripts()
        elif choice == "0":
            await revert_changes()
        elif choice.lower() == "s":
            await smart_mode()
        elif choice.lower() == "q":
            clear_screen()
            print(f"\n  {Colors.CYAN}Thanks for using UltimatePing!{Colors.RESET}")
            print(f"  {Colors.DIM}Better ping, better gaming.{Colors.RESET}\n")
            break
        else:
            print_error("Invalid choice.")
            await asyncio.sleep(1)


if __name__ == "__main__":
    # Frozen exe (PyInstaller) → always launch GUI
    # python main.py --gui   → launch GUI
    # python main.py         → launch CLI
    if getattr(sys, "frozen", False) or "--gui" in sys.argv:
        from gui import launch_gui
        launch_gui()
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print(f"\n\n  {Colors.CYAN}Goodbye!{Colors.RESET}\n")
