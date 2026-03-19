"""
UltimatePing — Premium Gaming Network Optimizer GUI
Built with CustomTkinter for a modern, polished dark-mode experience.
"""

import asyncio
import io
import platform
import threading
import time
from typing import Dict, List, Optional

try:
    import customtkinter as ctk
except ImportError:
    import sys
    sys.exit(
        "\n  customtkinter is required for the GUI.\n"
        "  Install:  pip install customtkinter\n"
    )

import tkinter as tk
from tkinter import messagebox

try:
    import pyconify
    import cairosvg
    from PIL import Image as PILImage
    _HAS_ICONS = True
except ImportError:
    _HAS_ICONS = False

from config import GAME_SERVERS, OptimizationConfig
from network_scanner import scan_servers, tcp_ping
from route_optimizer import find_optimal_mtu
from dns_optimizer import benchmark_all_dns, get_current_dns
from tcp_udp_tuner import (
    GAMING_PROFILES, GAME_PROFILE_MAP,
    get_profile_for_game, get_current_socket_settings, generate_optimization_report,
    get_intelligent_profile,
)
from ping_monitor import PingMonitor, MonitorStats, PingSnapshot
from os_optimizer import (
    get_optimizations, read_current_values,
    apply_optimization, revert_optimization,
    apply_all_optimizations, revert_all_optimizations,
    apply_intelligent_optimizations,
    generate_optimization_script, generate_revert_script,
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
    NetworkCondition,
    intelligent_dns_select,
    intelligent_route_analyze,
    intelligent_socket_config,
    intelligent_os_config,
    choose_monitor_strategy,
    choose_dns_strategy,
    choose_route_strategy,
    adaptive_scan_config,
    DNSHistory,
    RouteHistory,
    IntelligentMonitor,
)


# ─── Appearance ──────────────────────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ─── Design Tokens ───────────────────────────────────────────────────────────

class C:
    """Full colour palette — dark gaming aesthetic."""

    # backgrounds
    BG_ROOT   = "#060a10"
    BG        = "#0c1017"
    BG_CARD   = "#121a26"
    BG_RAISED = "#1a2332"
    BG_INPUT  = "#141e2c"
    BG_HOVER  = "#1e2d42"

    # accent
    PRIMARY       = "#7c3aed"
    PRIMARY_HOVER = "#a78bfa"
    PRIMARY_DIM   = "#5b21b6"
    PRIMARY_GLOW  = "#7c3aed30"

    # semantic
    SUCCESS     = "#34d399"
    SUCCESS_DIM = "#059669"
    WARNING     = "#fbbf24"
    WARNING_DIM = "#d97706"
    ERROR       = "#f87171"
    ERROR_DIM   = "#b91c1c"

    # data colours
    CYAN   = "#22d3ee"
    BLUE   = "#60a5fa"
    PURPLE = "#c084fc"
    PINK   = "#f472b6"
    ORANGE = "#fb923c"
    LIME   = "#a3e635"

    # text
    TEXT       = "#f1f5f9"
    TEXT_SEC   = "#94a3b8"
    TEXT_MUTED = "#475569"

    # borders
    BORDER       = "#1e293b"
    BORDER_LIGHT = "#334155"
    BORDER_GLOW  = "#7c3aed40"

    # sidebar
    SIDEBAR     = "#080c14"
    SIDEBAR_SEL = "#141c2e"
    INDICATOR   = "#7c3aed"


# ─── Async helper ────────────────────────────────────────────────────────────

def _run_async(coro, callback=None):
    """Run *coro* in a daemon thread; call *callback*(result | Exception)."""
    def _worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            res = loop.run_until_complete(coro)
            if callback:
                callback(res)
        except Exception as exc:
            if callback:
                callback(exc)
        finally:
            loop.close()
    threading.Thread(target=_worker, daemon=True).start()


# ─── Tiny helpers ────────────────────────────────────────────────────────────

def _ping_color(ms: float) -> str:
    if ms <= 0:
        return C.ERROR
    if ms < 30:
        return C.SUCCESS
    if ms < 60:
        return C.WARNING
    if ms < 100:
        return C.ORANGE
    return C.ERROR


def _servers_for(game: str, region: str) -> List[str]:
    if region == "ALL":
        out: List[str] = []
        for r in GAME_SERVERS.get(game, {}).values():
            out.extend(r)
        return out
    return list(GAME_SERVERS.get(game, {}).get(region, []))


# ─── Icon System (pyconify + cairosvg) ──────────────────────────────────────

_icon_cache: Dict[str, ctk.CTkImage] = {}


def _icon(name: str, size: int = 20, color: str = "#94a3b8") -> Optional[ctk.CTkImage]:
    """Render an Iconify SVG icon as a CTkImage via pyconify + cairosvg."""
    if not _HAS_ICONS:
        return None
    key = f"{name}:{size}:{color}"
    if key in _icon_cache:
        return _icon_cache[key]
    try:
        svg_data = pyconify.svg(name, color=color, height=size)
        hi = size * 2
        png_data = cairosvg.svg2png(bytestring=svg_data, output_width=hi, output_height=hi)
        img = PILImage.open(io.BytesIO(png_data))
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        _icon_cache[key] = ctk_img
        return ctk_img
    except Exception:
        return None


# ─── Custom Widgets ──────────────────────────────────────────────────────────

class NavButton(ctk.CTkFrame):
    """Sidebar nav item with SVG icon and active indicator bar."""

    def __init__(self, master, icon_name: str, text: str, command=None, **kw):
        super().__init__(master, fg_color="transparent", corner_radius=8, height=44, **kw)
        self.pack_propagate(False)
        self._cmd = command
        self._active = False
        self._icon_name = icon_name

        # pre-render both icon states
        self._img_normal = _icon(icon_name, 19, C.TEXT_MUTED)
        self._img_active = _icon(icon_name, 19, C.PRIMARY_HOVER)

        self._bar = ctk.CTkFrame(self, width=3, corner_radius=2, fg_color="transparent")
        self._bar.pack(side="left", fill="y")

        if self._img_normal:
            self._icon_lbl = ctk.CTkLabel(self, text="", image=self._img_normal, width=36)
        else:
            self._icon_lbl = ctk.CTkLabel(
                self, text="●", font=("Segoe UI", 14),
                text_color=C.TEXT_MUTED, width=36,
            )
        self._icon_lbl.pack(side="left", padx=(12, 4))

        self._label = ctk.CTkLabel(
            self, text=text, font=("Segoe UI", 13),
            text_color=C.TEXT_MUTED, anchor="w",
        )
        self._label.pack(side="left", fill="x", expand=True, padx=(2, 14))

        for w in (self, self._icon_lbl, self._label):
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)
            w.bind("<Button-1>", self._click)

    def _enter(self, _):
        if not self._active:
            self.configure(fg_color=C.BG_HOVER)

    def _leave(self, _):
        if not self._active:
            self.configure(fg_color="transparent")

    def _click(self, _):
        if self._cmd:
            self._cmd()

    def set_active(self, on: bool):
        self._active = on
        self.configure(fg_color=C.SIDEBAR_SEL if on else "transparent")
        self._bar.configure(fg_color=C.INDICATOR if on else "transparent")
        img = self._img_active if on else self._img_normal
        if img:
            self._icon_lbl.configure(image=img)
        self._label.configure(text_color=C.TEXT if on else C.TEXT_MUTED)


class StatCard(ctk.CTkFrame):
    """Dashboard metric card with SVG icon, title, and large value."""

    def __init__(
        self, master, title: str, value: str = "---",
        color: str = C.PRIMARY, icon_name: str = "", **kw,
    ):
        super().__init__(
            master, fg_color=C.BG_CARD, corner_radius=16,
            border_width=1, border_color=C.BORDER, **kw,
        )

        # accent stripe at top
        ctk.CTkFrame(
            self, fg_color=color, height=3, corner_radius=0,
        ).pack(fill="x", padx=16, pady=(12, 0))

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(10, 2))
        img = _icon(icon_name, 18, color) if icon_name else None
        if img:
            ctk.CTkLabel(top, text="", image=img).pack(side="left")
        ctk.CTkLabel(
            top, text=title.upper(),
            font=("Segoe UI", 10, "bold"), text_color=C.TEXT_MUTED,
        ).pack(side="left", padx=(8 if img else 0, 0))

        self._val = ctk.CTkLabel(
            self, text=value,
            font=("Consolas", 28, "bold"), text_color=color,
        )
        self._val.pack(padx=18, pady=(4, 18), anchor="w")

    def set(self, value: str, color: Optional[str] = None):
        self._val.configure(text=value)
        if color:
            self._val.configure(text_color=color)


class DataTable(ctk.CTkFrame):
    """Scrollable data table with styled header and alternating rows."""

    def __init__(
        self, master, columns: List[str],
        widths: Optional[Dict[str, int]] = None, **kw,
    ):
        super().__init__(
            master, fg_color=C.BG_CARD, corner_radius=14,
            border_width=1, border_color=C.BORDER, **kw,
        )
        self._cols = columns
        self._widths = widths or {}

        # ── header row ──
        hdr = ctk.CTkFrame(self, fg_color=C.BG_RAISED, corner_radius=0, height=38)
        hdr.pack(fill="x", padx=1, pady=(1, 0))
        hdr.pack_propagate(False)
        for c in columns:
            ctk.CTkLabel(
                hdr, text=c.upper(), font=("Segoe UI", 10, "bold"),
                text_color=C.TEXT_MUTED,
                width=self._widths.get(c, 120), anchor="center",
            ).pack(side="left", padx=6)

        # ── scrollable body ──
        self._body = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=C.BG_HOVER,
            scrollbar_button_hover_color=C.BORDER_LIGHT,
        )
        self._body.pack(fill="both", expand=True, padx=1, pady=1)

        self._rows: List[ctk.CTkFrame] = []
        self._n = 0

    def clear(self):
        for r in self._rows:
            r.destroy()
        self._rows.clear()
        self._n = 0

    def add_row(self, values: tuple, highlight: bool = False):
        bg = C.BG_RAISED if self._n % 2 else "transparent"
        if highlight:
            bg = "#1a1540"
        row = ctk.CTkFrame(self._body, fg_color=bg, corner_radius=0, height=34)
        row.pack(fill="x")
        row.pack_propagate(False)
        for col, val in zip(self._cols, values):
            ctk.CTkLabel(
                row, text=str(val), font=("Consolas", 11),
                text_color=C.TEXT if not highlight else C.PRIMARY_HOVER,
                width=self._widths.get(col, 120), anchor="center",
            ).pack(side="left", padx=6)
        self._rows.append(row)
        self._n += 1


class PingGraph(tk.Canvas):
    """Canvas-based real-time latency graph with gradient fill."""

    def __init__(self, master, height: int = 220, **kw):
        super().__init__(master, bg=C.BG_CARD, highlightthickness=0, height=height, **kw)
        self._data: List[float] = []
        self._max_pts = 200
        self._gw = 600
        self._gh = height
        self.bind("<Configure>", self._resize)

    def _resize(self, e):
        self._gw = e.width
        self._gh = e.height
        self._max_pts = max(60, self._gw // 3)
        self._render()

    def add_point(self, ms: float):
        self._data.append(ms)
        if len(self._data) > self._max_pts:
            self._data = self._data[-self._max_pts:]
        self._render()

    def clear_data(self):
        self._data.clear()
        self.delete("all")

    def _render(self):
        self.delete("all")
        n = len(self._data)
        if n < 2:
            return

        P = {"t": 28, "b": 28, "l": 58, "r": 18}
        gw = self._gw - P["l"] - P["r"]
        gh = self._gh - P["t"] - P["b"]
        if gw < 40 or gh < 20:
            return

        valid = [d for d in self._data if d > 0]
        if not valid:
            return
        lo = max(0, min(valid) - 5)
        hi = max(valid) + 10
        span = (hi - lo) or 1

        # grid lines
        for i in range(5):
            y = P["t"] + gh * i / 4
            v = hi - span * i / 4
            self.create_line(P["l"], y, self._gw - P["r"], y, fill="#1e293b", dash=(2, 6))
            self.create_text(
                P["l"] - 6, y, text=f"{v:.0f}",
                fill=C.TEXT_MUTED, font=("Consolas", 8), anchor="e",
            )

        # build point coords
        step = gw / max(n - 1, 1)
        pts = []
        for i, v in enumerate(self._data):
            x = P["l"] + i * step
            y = P["t"] + gh * (1 - (max(v, 0) - lo) / span) if v > 0 else P["t"] + gh
            pts.append((x, y))

        # area fill
        fp = list(pts) + [(pts[-1][0], P["t"] + gh), (pts[0][0], P["t"] + gh)]
        self.create_polygon([c for p in fp for c in p], fill="#160f30", outline="")

        # line segments colour-coded
        for i in range(1, len(pts)):
            c = _ping_color(self._data[i])
            self.create_line(*pts[i - 1], *pts[i], fill=c, width=2, smooth=True)

        # glow dot on latest point
        lx, ly = pts[-1]
        self.create_oval(lx - 9, ly - 9, lx + 9, ly + 9, fill="#2d1b69", outline="")
        self.create_oval(lx - 4, ly - 4, lx + 4, ly + 4, fill=C.PRIMARY, outline="")

        # axis label + current value
        self.create_text(
            P["l"], 10, text="ms", fill=C.TEXT_MUTED, font=("Consolas", 9), anchor="w",
        )
        if self._data[-1] > 0:
            self.create_text(
                self._gw - P["r"], 10, text=f"{self._data[-1]:.1f} ms",
                fill=C.PRIMARY_HOVER, font=("Consolas", 11, "bold"), anchor="e",
            )


class Toast(ctk.CTkFrame):
    """Non-blocking slide-in notification toast with SVG icons."""

    _stack: List["Toast"] = []
    _TOAST_H = 44
    _GAP = 10
    _Y0 = 12

    _ICON_MAP = {
        "info":    "lucide:info",
        "success": "lucide:check-circle-2",
        "warning": "lucide:alert-triangle",
        "error":   "lucide:x-circle",
    }

    def __init__(self, parent, message: str, kind: str = "info", duration: int = 3500):
        accent = {
            "info": C.PRIMARY, "success": C.SUCCESS,
            "warning": C.WARNING, "error": C.ERROR,
        }.get(kind, C.PRIMARY)

        super().__init__(
            parent, fg_color=C.BG_RAISED, corner_radius=12,
            border_width=1, border_color=accent, height=self._TOAST_H,
        )
        self.pack_propagate(False)

        ctk.CTkFrame(self, fg_color=accent, width=4, corner_radius=2).pack(
            side="left", fill="y",
        )
        toast_icon = _icon(self._ICON_MAP.get(kind, "lucide:info"), 16, accent)
        if toast_icon:
            ctk.CTkLabel(
                self, text="", image=toast_icon, width=28,
            ).pack(side="left", padx=(10, 0))
        ctk.CTkLabel(
            self, text=message, font=("Segoe UI", 12), text_color=C.TEXT,
        ).pack(side="left", padx=(6, 18), pady=10)

        Toast._stack.append(self)
        self._reposition_all()
        self.lift()
        parent.after(duration, self._dismiss)

    @classmethod
    def _reposition_all(cls):
        for i, toast in enumerate(cls._stack):
            y = cls._Y0 + i * (cls._TOAST_H + cls._GAP)
            toast.place(relx=1.0, y=y, anchor="ne", x=-14)

    def _dismiss(self):
        if self in Toast._stack:
            Toast._stack.remove(self)
        self.place_forget()
        self.destroy()
        Toast._reposition_all()


# ─── Page: Dashboard ─────────────────────────────────────────────────────────

class DashboardPage(ctk.CTkFrame):

    def __init__(self, master, app: "App"):
        super().__init__(master, fg_color=C.BG, corner_radius=0)
        self.app = app
        self._build()

    # ── layout ──

    def _build(self):
        # title row
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=32, pady=(28, 2))
        _hdr_icon = _icon("lucide:layout-dashboard", 22, C.PRIMARY_HOVER)
        if _hdr_icon:
            ctk.CTkLabel(hdr, text="", image=_hdr_icon).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            hdr, text="Dashboard",
            font=("Segoe UI", 22, "bold"), text_color=C.TEXT,
        ).pack(side="left")
        ctk.CTkLabel(
            self, text="Real-time overview and quick optimization actions",
            font=("Segoe UI", 12), text_color=C.TEXT_SEC,
        ).pack(anchor="w", padx=32)

        # stat cards
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.pack(fill="x", padx=32, pady=18)
        cards.columnconfigure((0, 1, 2, 3), weight=1)

        self.c_ping = StatCard(cards, "Ping", "---", C.BLUE, "lucide:signal")
        self.c_ping.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.c_jitter = StatCard(cards, "Jitter", "---", C.CYAN, "lucide:bar-chart-3")
        self.c_jitter.grid(row=0, column=1, sticky="nsew", padx=8)
        self.c_loss = StatCard(cards, "Packet Loss", "---", C.SUCCESS, "lucide:package-x")
        self.c_loss.grid(row=0, column=2, sticky="nsew", padx=8)
        self.c_score = StatCard(cards, "Stability", "---", C.PURPLE, "lucide:star")
        self.c_score.grid(row=0, column=3, sticky="nsew", padx=(8, 0))

        # quick actions
        ctk.CTkLabel(
            self, text="QUICK ACTIONS",
            font=("Segoe UI", 11, "bold"), text_color=C.TEXT_MUTED,
        ).pack(anchor="w", padx=34, pady=(6, 8))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=32)
        for txt, ico, cmd, fg in [
            ("Full Optimize", "lucide:rocket", self._full, C.PRIMARY),
            ("Quick Scan",    "lucide:radar",  self._scan, C.BG_RAISED),
            ("Best DNS",      "lucide:globe",  self._dns,  C.BG_RAISED),
            ("Apply Tweaks",  "lucide:settings", self._tweaks, C.BG_RAISED),
        ]:
            btn_icon = _icon(ico, 16, C.TEXT)
            ctk.CTkButton(
                btns, text=f"  {txt}", command=cmd,
                image=btn_icon, compound="left",
                fg_color=fg,
                hover_color=C.PRIMARY_HOVER if fg == C.PRIMARY else C.BG_HOVER,
                corner_radius=10, height=42,
                font=("Segoe UI", 12, "bold"), text_color=C.TEXT,
            ).pack(side="left", padx=(0, 10))

        # activity log
        ctk.CTkLabel(
            self, text="ACTIVITY LOG",
            font=("Segoe UI", 11, "bold"), text_color=C.TEXT_MUTED,
        ).pack(anchor="w", padx=34, pady=(18, 6))

        self.log = ctk.CTkTextbox(
            self, fg_color=C.BG_CARD, text_color=C.TEXT,
            font=("Consolas", 11), corner_radius=12,
            border_width=1, border_color=C.BORDER,
            wrap="word", state="disabled",
        )
        self.log.pack(fill="both", expand=True, padx=32, pady=(0, 24))
        for tag, color in [
            ("ok", C.SUCCESS), ("err", C.ERROR), ("info", C.BLUE),
            ("warn", C.WARNING), ("head", C.PURPLE),
        ]:
            self.log._textbox.tag_configure(tag, foreground=color)

    # ── log helper ──

    def _write(self, msg: str, tag: str = ""):
        self.log.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.log._textbox.insert("end", f"[{ts}] ", "info")
        self.log._textbox.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    # ── actions ──

    def _full(self):
        game = self.app.selected_game()
        region = self.app.selected_region()
        if not game:
            Toast(self.app, "Select a game on the Scanner page first.", "warning")
            return
        servers = _servers_for(game, region)
        if not servers:
            Toast(self.app, "No servers for this selection.", "warning")
            return

        self._write("🧠 Starting intelligent full optimization…", "head")
        self.app.set_status("🧠 Optimizing…")

        async def _go():
            results = []
            # Step 0: Assess network
            cond = await assess_network()
            results.append(("cond", cond))
            # Step 1: Adaptive scan
            scan_cfg = adaptive_scan_config(cond, game)
            scan = await scan_servers(servers, scan_cfg, use_tcp=True)
            results.append(("scan", scan))
            target = scan[0].host if scan and scan[0].is_reachable else servers[0]
            # Step 2: Intelligent DNS
            best_dns, dns_recs = await intelligent_dns_select(game)
            results.append(("dns", (best_dns, dns_recs)))
            # Step 3: Intelligent route
            route, route_recs = await intelligent_route_analyze(target, game)
            results.append(("route", (route, route_recs)))
            # Step 4: MTU
            mtu = await find_optimal_mtu(target)
            results.append(("mtu", mtu))
            # Step 5: Intelligent socket config
            sock_cfg, sock_recs = intelligent_socket_config(cond, game)
            results.append(("socket", (sock_cfg, sock_recs)))
            # Step 6: Intelligent OS config
            os_cfg, os_recs = intelligent_os_config(cond, game)
            results.append(("os", (os_cfg, os_recs)))
            return results

        def _done(res):
            if isinstance(res, Exception):
                self.after(0, lambda: self._write(f"Error: {res}", "err"))
                return

            def _ui():
                for k, d in res:
                    if k == "cond":
                        qc = {"excellent": "🟢", "good": "🟢", "fair": "🟡", "poor": "🔴", "bad": "🔴"}
                        self._write(f"Network: {qc.get(d.quality, '')} {d.quality.upper()} — "
                                    f"{d.base_latency_ms}ms, jitter {d.jitter_ms}ms", "ok")
                    elif k == "scan" and d and d[0].is_reachable:
                        b = d[0]
                        self.c_ping.set(f"{b.latency_ms}ms", _ping_color(b.latency_ms))
                        self.c_loss.set(
                            f"{b.packet_loss}%",
                            C.SUCCESS if b.packet_loss < 2 else C.ERROR,
                        )
                        hist = PerformanceHistory()
                        h = hist.get(b.host)
                        flag = " ★ history" if h and h.samples >= 3 else ""
                        self._write(f"Best: {b.host} ({b.latency_ms}ms){flag}", "ok")
                    elif k == "dns":
                        best_dns, dns_recs = d
                        if best_dns:
                            self._write(f"DNS: {best_dns.provider} ({best_dns.avg_ms}ms, score {best_dns.score}/100)", "ok")
                    elif k == "route":
                        route, route_recs = d
                        self._write(f"Route: {route.route_quality.upper()} ({route.total_hops} hops)", "ok")
                        for r in route_recs:
                            if r.priority <= 2:
                                self._write(f"  ⚠ {r.title}", "warn")
                    elif k == "mtu":
                        self._write(f"MTU: {d}", "ok")
                    elif k == "socket":
                        sock_cfg, _ = d
                        self._write(f"Socket: {sock_cfg.reason}", "info")
                    elif k == "os":
                        os_cfg, _ = d
                        self._write(f"OS: {os_cfg.reason} ({len(os_cfg.recommended_indices)} tweaks)", "info")
                self._write("🧠 Intelligent optimization complete!", "head")
                self.app.set_status("Intelligent optimization complete")
                Toast(self.app, "🧠 Intelligent optimization finished!", "success")

            self.after(0, _ui)

        _run_async(_go(), _done)

    def _scan(self):
        self._write("Quick connectivity test…", "info")
        self.app.set_status("Scanning…")

        async def _go():
            out = []
            for name, host, port in [
                ("Google", "8.8.8.8", 53),
                ("Cloudflare", "1.1.1.1", 80),
            ]:
                lat = await tcp_ping(host, port=port, timeout=3.0)
                out.append((name, lat))
            return out

        def _done(res):
            if isinstance(res, Exception):
                self.after(0, lambda: self._write(f"Error: {res}", "err"))
                return

            def _ui():
                for name, lat in res:
                    if lat > 0:
                        self._write(f"{name}: {lat:.1f}ms", "ok")
                    else:
                        self._write(f"{name}: unreachable", "err")
                best = min(
                    (r for r in res if r[1] > 0), key=lambda x: x[1], default=None,
                )
                if best:
                    self.c_ping.set(f"{best[1]:.0f}ms", _ping_color(best[1]))
                self.app.set_status("Ready")

            self.after(0, _ui)

        _run_async(_go(), _done)

    def _dns(self):
        self._write("🧠 Intelligent DNS selection…", "info")
        self.app.set_status("Testing DNS…")
        game = self.app.selected_game()

        def _done(res):
            if isinstance(res, Exception):
                self.after(0, lambda: self._write(f"Error: {res}", "err"))
                return

            def _ui():
                best_dns, recs = res
                if best_dns:
                    self._write(
                        f"Best DNS: {best_dns.provider} ({best_dns.ip}) – "
                        f"{best_dns.avg_ms}ms, score {best_dns.score}/100",
                        "ok",
                    )
                    Toast(self.app, f"Best DNS: {best_dns.provider}", "success")
                else:
                    self._write("Could not determine best DNS.", "warn")
                self.app.set_status("Ready")

            self.after(0, _ui)

        _run_async(intelligent_dns_select(game), _done)

    def _tweaks(self):
        self._write("🧠 Applying intelligent OS optimizations…", "info")
        game = self.app.selected_game()
        results, skipped = apply_intelligent_optimizations(game)
        ok = sum(1 for s, _ in results if s)
        for s, m in results:
            self._write(m, "ok" if s else "err")
        if skipped:
            self._write(f"Skipped ({len(skipped)}): {', '.join(skipped)}", "info")
        self._write(f"Done — {ok}/{len(results)} applied intelligently.", "head")
        Toast(
            self.app,
            f"Applied {ok}/{len(results)} tweaks ({len(skipped)} skipped)",
            "success" if ok else "warning",
        )


# ─── Page: Server Scanner ────────────────────────────────────────────────────

class ScannerPage(ctk.CTkFrame):

    def __init__(self, master, app: "App"):
        super().__init__(master, fg_color=C.BG, corner_radius=0)
        self.app = app
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=32, pady=(28, 12))
        _hdr_icon = _icon("lucide:radar", 22, C.PRIMARY_HOVER)
        if _hdr_icon:
            ctk.CTkLabel(hdr, text="", image=_hdr_icon).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            hdr, text="Server Scanner",
            font=("Segoe UI", 22, "bold"), text_color=C.TEXT,
        ).pack(side="left")

        # selection row
        sel = ctk.CTkFrame(self, fg_color="transparent")
        sel.pack(fill="x", padx=32, pady=(0, 8))

        ctk.CTkLabel(
            sel, text="Game", font=("Segoe UI", 12), text_color=C.TEXT_SEC,
        ).pack(side="left", padx=(0, 6))

        games = [g.replace("_", " ").title() for g in GAME_SERVERS if g != "custom"]
        self.game_var = ctk.StringVar(value=games[0] if games else "")
        self.game_menu = ctk.CTkOptionMenu(
            sel, variable=self.game_var, values=games,
            fg_color=C.BG_INPUT, button_color=C.BG_RAISED,
            button_hover_color=C.BG_HOVER, dropdown_fg_color=C.BG_CARD,
            dropdown_hover_color=C.BG_HOVER, dropdown_text_color=C.TEXT,
            text_color=C.TEXT, font=("Segoe UI", 12), width=180,
            command=self._game_changed,
        )
        self.game_menu.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            sel, text="Region", font=("Segoe UI", 12), text_color=C.TEXT_SEC,
        ).pack(side="left", padx=(0, 6))

        self.region_var = ctk.StringVar(value="ALL")
        self.region_menu = ctk.CTkOptionMenu(
            sel, variable=self.region_var, values=["ALL"],
            fg_color=C.BG_INPUT, button_color=C.BG_RAISED,
            button_hover_color=C.BG_HOVER, dropdown_fg_color=C.BG_CARD,
            dropdown_hover_color=C.BG_HOVER, dropdown_text_color=C.TEXT,
            text_color=C.TEXT, font=("Segoe UI", 12), width=140,
        )
        self.region_menu.pack(side="left", padx=(0, 20))

        _scan_icon = _icon("lucide:search", 16, C.TEXT)
        ctk.CTkButton(
            sel, text="  Scan Servers", command=self._scan,
            image=_scan_icon, compound="left",
            fg_color=C.SUCCESS_DIM, hover_color=C.SUCCESS,
            corner_radius=10, height=36,
            font=("Segoe UI", 12, "bold"), text_color=C.TEXT,
        ).pack(side="left")

        # custom server entry
        cust = ctk.CTkFrame(self, fg_color="transparent")
        cust.pack(fill="x", padx=32, pady=(0, 12))
        ctk.CTkLabel(
            cust, text="Custom", font=("Segoe UI", 12), text_color=C.TEXT_SEC,
        ).pack(side="left", padx=(0, 6))
        self.custom_entry = ctk.CTkEntry(
            cust, placeholder_text="e.g. 192.168.1.1, game.server.com",
            fg_color=C.BG_INPUT, border_color=C.BORDER,
            text_color=C.TEXT, font=("Consolas", 12), width=380, height=36,
        )
        self.custom_entry.pack(side="left")

        # results
        self.table = DataTable(
            self,
            columns=["Server", "IP", "Ping (ms)", "Loss %", "Status"],
            widths={
                "Server": 220, "IP": 160,
                "Ping (ms)": 100, "Loss %": 80, "Status": 100,
            },
        )
        self.table.pack(fill="both", expand=True, padx=32, pady=(0, 24))
        self._game_changed(self.game_var.get())

    def _game_changed(self, _=None):
        key = self.game_var.get().lower().replace(" ", "_")
        regions = ["ALL"] + list(GAME_SERVERS.get(key, {}).keys())
        self.region_menu.configure(values=regions)
        self.region_var.set("ALL")

    def game_key(self) -> str:
        return self.game_var.get().lower().replace(" ", "_")

    def region(self) -> str:
        return self.region_var.get()

    def _scan(self):
        custom = self.custom_entry.get().strip()
        if custom:
            servers = [s.strip() for s in custom.split(",") if s.strip()]
        else:
            servers = _servers_for(self.game_key(), self.region())

        if not servers:
            Toast(self.app, "No servers to scan.", "warning")
            return

        self.table.clear()
        self.app.set_status(f"🧠 Scanning {len(servers)} server(s) (adaptive)…")

        async def _go():
            cond = await assess_network()
            scan_cfg = adaptive_scan_config(cond, self.game_key())
            results = await scan_servers(servers, scan_cfg, use_tcp=True)
            return cond, results

        def _done(res):
            if isinstance(res, Exception):
                self.after(0, lambda: Toast(self.app, str(res), "error"))
                return

            def _ui():
                cond, scan_results = res
                self.table.clear()
                hist = PerformanceHistory()
                for r in scan_results:
                    status = "● ONLINE" if r.is_reachable else "○ OFFLINE"
                    ping = f"{r.latency_ms}" if r.is_reachable else "---"
                    h = hist.get(r.host)
                    score_str = f"({h.score}/100)" if h and h.samples > 0 else ""
                    display_status = f"{status} {score_str}".strip()
                    self.table.add_row(
                        (r.host, r.ip, ping, f"{r.packet_loss}", display_status),
                        highlight=(r == scan_results[0] and r.is_reachable),
                    )
                quality = cond.quality.upper()
                self.app.set_status(f"Scan complete — {len(scan_results)} servers — Network: {quality}")
                if scan_results and scan_results[0].is_reachable:
                    self.app.set_ping(
                        f"Best: {scan_results[0].latency_ms}ms",
                        _ping_color(scan_results[0].latency_ms),
                    )

            self.after(0, _ui)

        _run_async(_go(), _done)


# ─── Page: DNS Optimizer ─────────────────────────────────────────────────────

class DNSPage(ctk.CTkFrame):

    def __init__(self, master, app: "App"):
        super().__init__(master, fg_color=C.BG, corner_radius=0)
        self.app = app
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=32, pady=(28, 12))
        _hdr_icon = _icon("lucide:globe", 22, C.PRIMARY_HOVER)
        if _hdr_icon:
            ctk.CTkLabel(top, text="", image=_hdr_icon).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            top, text="DNS Optimizer",
            font=("Segoe UI", 22, "bold"), text_color=C.TEXT,
        ).pack(side="left")
        _bench_icon = _icon("lucide:play", 16, C.TEXT)
        ctk.CTkButton(
            top, text="  Benchmark All", command=self._bench,
            image=_bench_icon, compound="left",
            fg_color=C.SUCCESS_DIM, hover_color=C.SUCCESS,
            corner_radius=10, height=36,
            font=("Segoe UI", 12, "bold"), text_color=C.TEXT,
        ).pack(side="right")

        # current DNS
        info = ctk.CTkFrame(
            self, fg_color=C.BG_CARD, corner_radius=12,
            border_width=1, border_color=C.BORDER,
        )
        info.pack(fill="x", padx=32, pady=(0, 14))
        current = get_current_dns()
        _dns_info_icon = _icon("lucide:server", 14, C.CYAN)
        dns_lbl = ctk.CTkLabel(
            info, text=f"  Current DNS:  {', '.join(current)}",
            font=("Consolas", 12), text_color=C.CYAN,
        )
        if _dns_info_icon:
            dns_lbl.configure(image=_dns_info_icon, compound="left")
        dns_lbl.pack(anchor="w", padx=14, pady=10)

        self.table = DataTable(
            self,
            columns=["Provider", "IP", "Avg (ms)", "Min (ms)", "Max (ms)", "Reliability"],
            widths={
                "Provider": 140, "IP": 140, "Avg (ms)": 100,
                "Min (ms)": 100, "Max (ms)": 100, "Reliability": 100,
            },
        )
        self.table.pack(fill="both", expand=True, padx=32, pady=(0, 24))

    def _bench(self):
        self.table.clear()
        self.app.set_status("🧠 Intelligent DNS benchmark…")
        config = OptimizationConfig.load()
        game = self.app.selected_game()

        async def _go():
            # Run both intelligent selection and full benchmark
            best_dns, recs = await intelligent_dns_select(game)
            dns_results = await benchmark_all_dns(config)
            return best_dns, recs, dns_results

        def _done(res):
            if isinstance(res, Exception):
                self.after(0, lambda: Toast(self.app, str(res), "error"))
                return

            def _ui():
                best_dns, recs, dns_results = res
                self.table.clear()
                for i, r in enumerate(dns_results):
                    if r.resolved_correctly:
                        score = f"{getattr(r, '_sort_key', 0):.0f}" if hasattr(r, '_sort_key') else "—"
                        self.table.add_row(
                            (
                                r.name, r.primary_ip,
                                f"{r.avg_latency_ms:.1f}", f"{r.min_latency_ms:.1f}",
                                f"{r.max_latency_ms:.1f}", f"{r.reliability:.0f}%",
                            ),
                            highlight=(i == 0),
                        )
                    else:
                        self.table.add_row(
                            (r.name, r.primary_ip, "FAIL", "—", "—", "0%"),
                        )
                if best_dns:
                    Toast(
                        self.app,
                        f"🧠 Best: {best_dns.provider} ({best_dns.avg_ms:.0f}ms, "
                        f"score {best_dns.score}/100)",
                        "success",
                    )
                self.app.set_status("Intelligent DNS benchmark complete")

            self.after(0, _ui)

        _run_async(_go(), _done)


# ─── Page: Real-time Monitor ─────────────────────────────────────────────────

class MonitorPage(ctk.CTkFrame):

    def __init__(self, master, app: "App"):
        super().__init__(master, fg_color=C.BG, corner_radius=0)
        self.app = app
        self._monitor: Optional[PingMonitor] = None
        self._running = False
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=32, pady=(28, 12))
        _hdr_icon = _icon("lucide:activity", 22, C.PRIMARY_HOVER)
        if _hdr_icon:
            ctk.CTkLabel(hdr, text="", image=_hdr_icon).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            hdr, text="Real-time Monitor",
            font=("Segoe UI", 22, "bold"), text_color=C.TEXT,
        ).pack(side="left")

        # controls
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=32, pady=(0, 10))

        ctk.CTkLabel(
            ctrl, text="Target", font=("Segoe UI", 12), text_color=C.TEXT_SEC,
        ).pack(side="left", padx=(0, 6))

        self.target = ctk.CTkEntry(
            ctrl, text_color=C.TEXT, fg_color=C.BG_INPUT,
            border_color=C.BORDER, font=("Consolas", 12),
            width=260, height=36,
        )
        self.target.pack(side="left", padx=(0, 12))
        self.target.insert(0, "8.8.8.8")

        self._play_icon = _icon("lucide:play", 14, C.TEXT)
        self._stop_icon = _icon("lucide:square", 14, C.TEXT)
        self.toggle_btn = ctk.CTkButton(
            ctrl, text="  Start", command=self._toggle,
            image=self._play_icon, compound="left",
            fg_color=C.SUCCESS_DIM, hover_color=C.SUCCESS,
            corner_radius=10, height=36, width=120,
            font=("Segoe UI", 12, "bold"), text_color=C.TEXT,
        )
        self.toggle_btn.pack(side="left", padx=(0, 8))

        _clear_icon = _icon("lucide:trash-2", 14, C.TEXT_SEC)
        ctk.CTkButton(
            ctrl, text="  Clear", command=self._clear,
            image=_clear_icon, compound="left",
            fg_color=C.BG_RAISED, hover_color=C.BG_HOVER,
            corner_radius=10, height=36, width=100,
            font=("Segoe UI", 11), text_color=C.TEXT_SEC,
        ).pack(side="left")

        # graph
        gf = ctk.CTkFrame(
            self, fg_color=C.BG_CARD, corner_radius=14,
            border_width=1, border_color=C.BORDER,
        )
        gf.pack(fill="x", padx=32, pady=(0, 12))
        self.graph = PingGraph(gf, height=200)
        self.graph.pack(fill="x", padx=2, pady=2)

        # stat cards row
        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", padx=32)
        stats.columnconfigure(tuple(range(8)), weight=1)

        self._stat: Dict[str, ctk.CTkLabel] = {}
        for i, (name, color) in enumerate([
            ("Current", C.PRIMARY), ("Average", C.TEXT),
            ("Min", C.SUCCESS), ("Max", C.ERROR),
            ("Jitter", C.WARNING), ("Loss", C.ORANGE),
            ("Spikes", C.PURPLE), ("Stability", C.CYAN),
        ]):
            card = ctk.CTkFrame(
                stats, fg_color=C.BG_CARD, corner_radius=12,
                border_width=1, border_color=C.BORDER,
            )
            card.grid(row=0, column=i, sticky="nsew", padx=3, pady=4)
            # accent dot
            ctk.CTkFrame(card, fg_color=color, height=2, corner_radius=0).pack(
                fill="x", padx=10, pady=(8, 0),
            )
            v = ctk.CTkLabel(
                card, text="---", font=("Consolas", 15, "bold"), text_color=color,
            )
            v.pack(padx=8, pady=(4, 2))
            ctk.CTkLabel(
                card, text=name.upper(), font=("Segoe UI", 8, "bold"), text_color=C.TEXT_MUTED,
            ).pack(pady=(0, 6))
            self._stat[name] = v

    def _toggle(self):
        if self._running:
            self._stop()
        else:
            self._start()

    def _start(self):
        t = self.target.get().strip()
        if not t:
            return
        self._running = True
        self.toggle_btn.configure(
            text="  Stop", image=self._stop_icon,
            fg_color=C.ERROR_DIM, hover_color=C.ERROR,
        )
        self.app.set_status(f"🧠 Monitoring {t} (intelligent)…")

        # Use intelligent monitor strategy
        async def _assess_and_start():
            cond = await assess_network()
            strat = choose_monitor_strategy(cond)
            return cond, strat

        def _done(res):
            if isinstance(res, Exception):
                interval = 0.8
            else:
                _, strat = res
                interval = strat.interval

            self._monitor = PingMonitor(t, interval=interval, history_size=500)

            def _on(snap: PingSnapshot, st: MonitorStats):
                self.after(0, lambda s=snap, ss=st: self._update(s, ss))

            self._monitor.on_update(_on)

            def _run():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._monitor.start())
                except Exception:
                    pass
                finally:
                    loop.close()

            threading.Thread(target=_run, daemon=True).start()

        _run_async(_assess_and_start(), _done)

    def _stop(self):
        self._running = False
        if self._monitor:
            self._monitor.stop()
        self.toggle_btn.configure(
            text="  Start", image=self._play_icon,
            fg_color=C.SUCCESS_DIM, hover_color=C.SUCCESS,
        )
        self.app.set_status("Monitor stopped")

    def _update(self, snap: PingSnapshot, st: MonitorStats):
        if not snap.is_timeout and snap.latency_ms > 0:
            self.graph.add_point(snap.latency_ms)

        def _fmt(v, inf=False):
            if inf and v >= 1e9:
                return "---"
            return f"{v:.1f}" if v > 0 else "---"

        self._stat["Current"].configure(
            text=f"{_fmt(st.current_ms)}ms" if st.current_ms > 0 else "---",
        )
        self._stat["Average"].configure(
            text=f"{_fmt(st.avg_ms)}ms" if st.avg_ms > 0 else "---",
        )
        self._stat["Min"].configure(text=f"{_fmt(st.min_ms, inf=True)}ms")
        self._stat["Max"].configure(
            text=f"{_fmt(st.max_ms)}ms" if st.max_ms > 0 else "---",
        )
        self._stat["Jitter"].configure(text=f"{st.jitter_ms:.1f}ms")
        self._stat["Loss"].configure(text=f"{st.packet_loss_pct:.1f}%")
        self._stat["Spikes"].configure(text=str(st.spike_count))
        self._stat["Stability"].configure(text=f"{st.stability_score:.0f}")

        c = _ping_color(st.current_ms) if st.current_ms > 0 else C.TEXT_MUTED
        self.app.set_ping(f"{st.current_ms:.0f}ms", c)

    def _clear(self):
        self.graph.clear_data()

    def on_leave(self):
        """Called when navigating away."""
        if self._running:
            self._stop()


# ─── Page: Route Analyzer ────────────────────────────────────────────────────

class RoutePage(ctk.CTkFrame):

    def __init__(self, master, app: "App"):
        super().__init__(master, fg_color=C.BG, corner_radius=0)
        self.app = app
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=32, pady=(28, 12))
        _hdr_icon = _icon("lucide:route", 22, C.PRIMARY_HOVER)
        if _hdr_icon:
            ctk.CTkLabel(hdr, text="", image=_hdr_icon).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            hdr, text="Route Analyzer",
            font=("Segoe UI", 22, "bold"), text_color=C.TEXT,
        ).pack(side="left")

        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=32, pady=(0, 10))

        ctk.CTkLabel(
            ctrl, text="Target", font=("Segoe UI", 12), text_color=C.TEXT_SEC,
        ).pack(side="left", padx=(0, 6))

        self.target = ctk.CTkEntry(
            ctrl, text_color=C.TEXT, fg_color=C.BG_INPUT,
            border_color=C.BORDER, font=("Consolas", 12),
            width=260, height=36,
        )
        self.target.pack(side="left", padx=(0, 12))
        self.target.insert(0, "8.8.8.8")

        _trace_icon = _icon("lucide:route", 16, C.TEXT)
        ctk.CTkButton(
            ctrl, text="  Trace Route", command=self._trace,
            image=_trace_icon, compound="left",
            fg_color=C.SUCCESS_DIM, hover_color=C.SUCCESS,
            corner_radius=10, height=36,
            font=("Segoe UI", 12, "bold"), text_color=C.TEXT,
        ).pack(side="left")

        self.info = ctk.CTkLabel(
            self, text="", font=("Segoe UI", 12), text_color=C.TEXT_SEC,
        )
        self.info.pack(anchor="w", padx=32, pady=(4, 8))

        self.table = DataTable(
            self,
            columns=["Hop", "IP", "Latency (ms)", "Note"],
            widths={"Hop": 60, "IP": 220, "Latency (ms)": 130, "Note": 180},
        )
        self.table.pack(fill="both", expand=True, padx=32, pady=(0, 24))

    def _trace(self):
        t = self.target.get().strip()
        if not t:
            return
        self.table.clear()
        self.info.configure(text=f"🧠 Intelligent route analysis to {t}…")
        self.app.set_status("🧠 Analyzing route…")
        game = self.app.selected_game()

        async def _go():
            route, recs = await intelligent_route_analyze(t, game)
            mtu = await find_optimal_mtu(t)
            # Check route history
            route_hist = RouteHistory()
            hist_rec = route_hist.get(t)
            return route, recs, mtu, hist_rec

        def _done(res):
            if isinstance(res, Exception):
                self.after(0, lambda: Toast(self.app, str(res), "error"))
                return

            def _ui():
                route, recs, mtu, hist_rec = res
                self.table.clear()
                for h in route.hops:
                    note = ""
                    if (
                        route.bottleneck_hop
                        and h.hop_number == route.bottleneck_hop.hop_number
                    ):
                        note = "⚠ BOTTLENECK"
                    if h.is_reachable:
                        self.table.add_row(
                            (str(h.hop_number), h.ip or "???",
                             f"{h.latency_ms:.1f}", note),
                            highlight=bool(note),
                        )
                    else:
                        self.table.add_row(
                            (str(h.hop_number), "* * *", "timeout", ""),
                        )

                info_parts = [
                    f"Quality: {route.route_quality.upper()}",
                    f"Hops: {route.total_hops}",
                    f"Avg: {route.avg_latency}ms",
                    f"MTU: {mtu}",
                ]
                if hist_rec and hist_rec.samples > 1:
                    info_parts.append(f"★ History: {hist_rec.samples} samples")
                self.info.configure(text="  │  ".join(info_parts))

                # Show intelligence recommendations
                if recs:
                    for r in recs[:3]:
                        Toast(self.app, f"[P{r.priority}] {r.title}", "warning" if r.priority <= 2 else "info")

                self.app.set_status("Intelligent route analysis complete")

            self.after(0, _ui)

        _run_async(_go(), _done)


# ─── Page: System Optimizer ──────────────────────────────────────────────────

class SystemPage(ctk.CTkFrame):

    def __init__(self, master, app: "App"):
        super().__init__(master, fg_color=C.BG, corner_radius=0)
        self.app = app
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=32, pady=(28, 12))

        hdr_row = ctk.CTkFrame(top, fg_color="transparent")
        hdr_row.pack(side="left")
        _hdr_icon = _icon("lucide:wrench", 22, C.PRIMARY_HOVER)
        if _hdr_icon:
            ctk.CTkLabel(hdr_row, text="", image=_hdr_icon).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            hdr_row, text=f"System Optimizer",
            font=("Segoe UI", 22, "bold"), text_color=C.TEXT,
        ).pack(side="left")
        ctk.CTkLabel(
            hdr_row, text=f"  {platform.system()}",
            font=("Segoe UI", 11), text_color=C.TEXT_MUTED,
        ).pack(side="left", padx=(6, 0))

        btns = ctk.CTkFrame(top, fg_color="transparent")
        btns.pack(side="right")

        _brain_icon = _icon("lucide:brain", 14, C.TEXT)
        ctk.CTkButton(
            btns, text="  Intelligent", command=self._apply_intelligent,
            image=_brain_icon, compound="left",
            fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
            corner_radius=10, height=34,
            font=("Segoe UI", 11, "bold"), text_color=C.TEXT,
        ).pack(side="left", padx=(0, 8))

        _check_icon = _icon("lucide:check-circle-2", 14, C.TEXT)
        ctk.CTkButton(
            btns, text="  Apply All", command=self._apply_all,
            image=_check_icon, compound="left",
            fg_color=C.SUCCESS_DIM, hover_color=C.SUCCESS,
            corner_radius=10, height=34,
            font=("Segoe UI", 11, "bold"), text_color=C.TEXT,
        ).pack(side="left", padx=(0, 8))

        _undo_icon = _icon("lucide:undo-2", 14, C.TEXT)
        ctk.CTkButton(
            btns, text="  Revert All", command=self._revert_all,
            image=_undo_icon, compound="left",
            fg_color=C.ERROR_DIM, hover_color=C.ERROR,
            corner_radius=10, height=34,
            font=("Segoe UI", 11, "bold"), text_color=C.TEXT,
        ).pack(side="left", padx=(0, 8))

        _export_icon = _icon("lucide:file-down", 14, C.TEXT_SEC)
        ctk.CTkButton(
            btns, text="  Export", command=self._export,
            image=_export_icon, compound="left",
            fg_color=C.BG_RAISED, hover_color=C.BG_HOVER,
            corner_radius=10, height=34,
            font=("Segoe UI", 11), text_color=C.TEXT_SEC,
        ).pack(side="left")

        # scrollable optimisation list
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=C.BG_HOVER,
            scrollbar_button_hover_color=C.BORDER_LIGHT,
        )
        self._scroll.pack(fill="both", expand=True, padx=32, pady=(0, 24))
        self._load()

    def _load(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        opts = read_current_values(get_optimizations())
        self._opts = opts

        for i, o in enumerate(opts):
            card = ctk.CTkFrame(
                self._scroll, fg_color=C.BG_CARD, corner_radius=10,
                border_width=1, border_color=C.BORDER,
            )
            card.pack(fill="x", pady=(0, 6))

            hdr = ctk.CTkFrame(card, fg_color="transparent")
            hdr.pack(fill="x", padx=14, pady=(12, 2))
            ctk.CTkLabel(
                hdr, text=o.name,
                font=("Segoe UI", 12, "bold"), text_color=C.TEXT,
            ).pack(side="left")
            if o.current_value:
                ctk.CTkLabel(
                    hdr, text=f"Current: {o.current_value}",
                    font=("Consolas", 10), text_color=C.CYAN,
                ).pack(side="right")

            ctk.CTkLabel(
                card, text=o.description,
                font=("Segoe UI", 11), text_color=C.TEXT_SEC,
                anchor="w", wraplength=600,
            ).pack(fill="x", padx=14, pady=(0, 6))

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=(0, 10))

            idx = i
            ctk.CTkButton(
                row, text="Apply", width=70, height=28, corner_radius=6,
                fg_color=C.SUCCESS_DIM, hover_color=C.SUCCESS,
                font=("Segoe UI", 10), text_color=C.TEXT,
                command=lambda j=idx: self._apply(j),
            ).pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                row, text="Revert", width=70, height=28, corner_radius=6,
                fg_color=C.ERROR_DIM, hover_color=C.ERROR,
                font=("Segoe UI", 10), text_color=C.TEXT,
                command=lambda j=idx: self._revert(j),
            ).pack(side="left")

    def _apply(self, idx):
        ok, msg = apply_optimization(self._opts[idx])
        Toast(self.app, msg, "success" if ok else "error")

    def _revert(self, idx):
        ok, msg = revert_optimization(self._opts[idx])
        Toast(self.app, msg, "success" if ok else "error")

    def _apply_all(self):
        if not messagebox.askyesno(
            "Confirm", "Apply all optimizations?\nThis may require admin/sudo.",
        ):
            return
        results = apply_all_optimizations()
        ok = sum(1 for s, _ in results if s)
        Toast(
            self.app,
            f"Applied {ok}/{len(results)} optimizations",
            "success" if ok else "warning",
        )

    def _apply_intelligent(self):
        """Apply only the optimizations the intelligence engine recommends."""
        if not messagebox.askyesno(
            "Intelligent Apply",
            "Apply network-condition-aware optimizations?\n"
            "The engine will skip tweaks not suited for your current network.",
        ):
            return
        game = self.app.selected_game()
        results, skipped = apply_intelligent_optimizations(game)
        ok = sum(1 for s, _ in results if s)
        Toast(
            self.app,
            f"🧠 Applied {ok}/{len(results)} (skipped {len(skipped)})",
            "success" if ok else "warning",
        )

    def _revert_all(self):
        if not messagebox.askyesno("Confirm", "Revert all optimizations to defaults?"):
            return
        results = revert_all_optimizations()
        ok = sum(1 for s, _ in results if s)
        Toast(
            self.app,
            f"Reverted {ok}/{len(results)} settings",
            "success" if ok else "warning",
        )

    def _export(self):
        config = OptimizationConfig.load()
        config.config_dir.mkdir(parents=True, exist_ok=True)
        ext = ".bat" if platform.system().lower() == "windows" else ".sh"

        opt_path = config.config_dir / f"optimize{ext}"
        opt_path.write_text(generate_optimization_script())
        rev_path = config.config_dir / f"revert{ext}"
        rev_path.write_text(generate_revert_script())

        if platform.system().lower() != "windows":
            opt_path.chmod(0o755)
            rev_path.chmod(0o755)

        Toast(self.app, f"Scripts saved to {config.config_dir}", "success")


# ─── Page: Socket Tuning ─────────────────────────────────────────────────────

class SocketsPage(ctk.CTkFrame):

    def __init__(self, master, app: "App"):
        super().__init__(master, fg_color=C.BG, corner_radius=0)
        self.app = app
        self._build()

    def _build(self):
        hdr_row = ctk.CTkFrame(self, fg_color="transparent")
        hdr_row.pack(anchor="w", padx=32, pady=(28, 12))
        _hdr_icon = _icon("lucide:wrench", 22, C.PRIMARY_HOVER)
        if _hdr_icon:
            ctk.CTkLabel(hdr_row, text="", image=_hdr_icon).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            hdr_row, text="TCP / UDP Socket Tuning",
            font=("Segoe UI", 22, "bold"), text_color=C.TEXT,
        ).pack(side="left")

        # current socket info
        info = ctk.CTkFrame(
            self, fg_color=C.BG_CARD, corner_radius=10,
            border_width=1, border_color=C.BORDER,
        )
        info.pack(fill="x", padx=32, pady=(0, 16))

        ctk.CTkLabel(
            info, text="Current System Socket Settings",
            font=("Segoe UI", 12, "bold"), text_color=C.PRIMARY,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        current = get_current_socket_settings()
        for k, v in current.items():
            ctk.CTkLabel(
                info, text=f"  {k}: {v:,}",
                font=("Consolas", 11), text_color=C.TEXT_SEC,
            ).pack(anchor="w", padx=16)
        ctk.CTkFrame(info, fg_color="transparent", height=10).pack()

        # profiles
        ctk.CTkLabel(
            self, text="Gaming Profiles",
            font=("Segoe UI", 15, "bold"), text_color=C.TEXT,
        ).pack(anchor="w", padx=32, pady=(4, 8))

        # Intelligent profile button
        intel_frame = ctk.CTkFrame(self, fg_color="transparent")
        intel_frame.pack(fill="x", padx=32, pady=(0, 8))
        _brain_icon = _icon("lucide:brain", 16, C.TEXT)
        ctk.CTkButton(
            intel_frame, text="  Generate Intelligent Profile",
            command=self._intelligent_profile,
            image=_brain_icon, compound="left",
            fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
            corner_radius=10, height=38,
            font=("Segoe UI", 12, "bold"), text_color=C.TEXT,
        ).pack(side="left")
        self._intel_label = ctk.CTkLabel(
            intel_frame, text="",
            font=("Segoe UI", 11), text_color=C.TEXT_SEC,
        )
        self._intel_label.pack(side="left", padx=(12, 0))

        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=C.BG_HOVER,
            scrollbar_button_hover_color=C.BORDER_LIGHT,
        )
        scroll.pack(fill="both", expand=True, padx=32, pady=(0, 24))

        for key, prof in GAMING_PROFILES.items():
            card = ctk.CTkFrame(
                scroll, fg_color=C.BG_CARD, corner_radius=10,
                border_width=1, border_color=C.BORDER,
            )
            card.pack(fill="x", pady=(0, 8))

            hdr = ctk.CTkFrame(card, fg_color="transparent")
            hdr.pack(fill="x", padx=16, pady=(12, 2))

            ctk.CTkLabel(
                hdr, text=prof.name,
                font=("Segoe UI", 13, "bold"), text_color=C.PRIMARY,
            ).pack(side="left")

            games_using = [
                g.replace("_", " ").title()
                for g, pk in GAME_PROFILE_MAP.items() if pk == key
            ]
            if games_using:
                ctk.CTkLabel(
                    hdr, text=f"Used by: {', '.join(games_using)}",
                    font=("Segoe UI", 10), text_color=C.TEXT_MUTED,
                ).pack(side="right")

            ctk.CTkLabel(
                card, text=prof.description,
                font=("Segoe UI", 11), text_color=C.TEXT_SEC,
                anchor="w", wraplength=600,
            ).pack(fill="x", padx=16, pady=(0, 8))

            pills = ctk.CTkFrame(card, fg_color="transparent")
            pills.pack(fill="x", padx=16, pady=(0, 12))

            for lbl, val in [
                ("TCP_NODELAY", "ON" if prof.tcp_nodelay else "OFF"),
                ("QUICKACK", "ON" if prof.tcp_quickack else "OFF"),
                ("Recv Buf", f"{prof.recv_buffer:,}"),
                ("Send Buf", f"{prof.send_buffer:,}"),
                (
                    "Keep-Alive",
                    f"{prof.keep_alive_interval}s" if prof.keep_alive else "OFF",
                ),
            ]:
                pill = ctk.CTkFrame(
                    pills, fg_color=C.BG_RAISED, corner_radius=6,
                )
                pill.pack(side="left", padx=(0, 6))
                ctk.CTkLabel(
                    pill, text=f"{lbl}: {val}",
                    font=("Consolas", 10), text_color=C.CYAN,
                ).pack(padx=10, pady=4)

    def _intelligent_profile(self):
        """Generate and display an intelligent socket profile based on network condition."""
        game = self.app.selected_game()
        self.app.set_status("🧠 Generating intelligent socket profile…")
        self._intel_label.configure(text="Analyzing network…")

        def _worker():
            profile = get_intelligent_profile(game)
            current = get_current_socket_settings()
            changes = generate_optimization_report(profile, current)
            return profile, changes

        def _done(res):
            if isinstance(res, Exception):
                self.after(0, lambda: Toast(self.app, str(res), "error"))
                return

            def _ui():
                profile, changes = res
                self._intel_label.configure(
                    text=f"{profile.name} — {profile.description}"
                )
                detail = "\n".join(changes) if changes else "No changes needed."
                Toast(self.app, f"🧠 {profile.name}", "success")
                self.app.set_status("Intelligent profile ready")

            self.after(0, _ui)

        def _thread():
            try:
                result = _worker()
                _done(result)
            except Exception as e:
                _done(e)

        threading.Thread(target=_thread, daemon=True).start()


# ─── Page: 🧠 Smart Mode ─────────────────────────────────────────────────────

class SmartPage(ctk.CTkFrame):
    """Intelligence engine page with auto-detect, learning and recommendations."""

    def __init__(self, master, app: "App"):
        super().__init__(master, fg_color=C.BG, corner_radius=0)
        self.app = app
        self._build()

    def _build(self):
        hdr_row = ctk.CTkFrame(self, fg_color="transparent")
        hdr_row.pack(anchor="w", padx=32, pady=(28, 2))
        _hdr_icon = _icon("lucide:brain-circuit", 22, C.PRIMARY_HOVER)
        if _hdr_icon:
            ctk.CTkLabel(hdr_row, text="", image=_hdr_icon).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            hdr_row, text="Smart Mode",
            font=("Segoe UI", 22, "bold"), text_color=C.TEXT,
        ).pack(side="left")
        ctk.CTkLabel(
            self, text="AI-powered analysis — auto-detect games, region, network and pick optimal servers",
            font=("Segoe UI", 12), text_color=C.TEXT_SEC,
        ).pack(anchor="w", padx=32)

        # status cards row
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.pack(fill="x", padx=32, pady=18)
        cards.columnconfigure((0, 1, 2, 3), weight=1)

        self.c_game = StatCard(cards, "Detected Game", "---", C.PINK, icon_name="lucide:gamepad-2")
        self.c_game.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.c_region = StatCard(cards, "Region", "---", C.CYAN, icon_name="lucide:globe")
        self.c_region.grid(row=0, column=1, sticky="nsew", padx=8)
        self.c_net = StatCard(cards, "Network", "---", C.SUCCESS, icon_name="lucide:wifi")
        self.c_net.grid(row=0, column=2, sticky="nsew", padx=8)
        self.c_server = StatCard(cards, "Best Server", "---", C.PRIMARY, icon_name="lucide:zap")
        self.c_server.grid(row=0, column=3, sticky="nsew", padx=(8, 0))

        # action buttons
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=32, pady=(0, 8))
        _brain_sm = _icon("lucide:brain", 16, C.TEXT)
        ctk.CTkButton(
            btns, text="  Run Smart Analysis", command=self._run_smart,
            image=_brain_sm, compound="left",
            fg_color=C.PRIMARY, hover_color=C.PRIMARY_HOVER,
            corner_radius=10, height=44, font=("Segoe UI", 13, "bold"),
            text_color=C.TEXT,
        ).pack(side="left", padx=(0, 10))
        _search_sm = _icon("lucide:search", 16, C.TEXT)
        ctk.CTkButton(
            btns, text="  Detect Games", command=self._detect_games,
            image=_search_sm, compound="left",
            fg_color=C.BG_RAISED, hover_color=C.BG_HOVER,
            corner_radius=10, height=44, font=("Segoe UI", 12, "bold"),
            text_color=C.TEXT,
        ).pack(side="left", padx=(0, 10))
        _globe_sm = _icon("lucide:globe", 16, C.TEXT)
        ctk.CTkButton(
            btns, text="  Detect Region", command=self._detect_region,
            image=_globe_sm, compound="left",
            fg_color=C.BG_RAISED, hover_color=C.BG_HOVER,
            corner_radius=10, height=44, font=("Segoe UI", 12, "bold"),
            text_color=C.TEXT,
        ).pack(side="left", padx=(0, 10))
        _wifi_sm = _icon("lucide:wifi", 16, C.TEXT)
        ctk.CTkButton(
            btns, text="  Assess Network", command=self._assess_net,
            image=_wifi_sm, compound="left",
            fg_color=C.BG_RAISED, hover_color=C.BG_HOVER,
            corner_radius=10, height=44, font=("Segoe UI", 12, "bold"),
            text_color=C.TEXT,
        ).pack(side="left")

        # recommendations + log area
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="both", expand=True, padx=32, pady=(4, 24))
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=1)
        bottom.rowconfigure(0, weight=1)

        # recommendations panel
        rec_frame = ctk.CTkFrame(
            bottom, fg_color=C.BG_CARD, corner_radius=12,
            border_width=1, border_color=C.BORDER,
        )
        rec_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        _lightbulb = _icon("lucide:lightbulb", 16, C.WARNING)
        rec_hdr = ctk.CTkFrame(rec_frame, fg_color="transparent")
        rec_hdr.pack(anchor="w", padx=16, pady=(12, 4))
        if _lightbulb:
            ctk.CTkLabel(rec_hdr, text="", image=_lightbulb).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            rec_hdr, text="Recommendations",
            font=("Segoe UI", 13, "bold"), text_color=C.TEXT,
        ).pack(side="left")

        self._rec_list = ctk.CTkScrollableFrame(
            rec_frame, fg_color="transparent",
            scrollbar_button_color=C.BG_HOVER,
            scrollbar_button_hover_color=C.BORDER_LIGHT,
        )
        self._rec_list.pack(fill="both", expand=True, padx=4, pady=(0, 8))
        self._rec_widgets: list = []

        # activity log
        log_frame = ctk.CTkFrame(
            bottom, fg_color=C.BG_CARD, corner_radius=12,
            border_width=1, border_color=C.BORDER,
        )
        log_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        _clipboard = _icon("lucide:clipboard-list", 16, C.BLUE)
        log_hdr = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_hdr.pack(anchor="w", padx=16, pady=(12, 4))
        if _clipboard:
            ctk.CTkLabel(log_hdr, text="", image=_clipboard).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            log_hdr, text="Intelligence Log",
            font=("Segoe UI", 13, "bold"), text_color=C.TEXT,
        ).pack(side="left")

        self._log = ctk.CTkTextbox(
            log_frame, fg_color=C.BG, text_color=C.TEXT,
            font=("Consolas", 11), corner_radius=8,
            wrap="word", state="disabled",
        )
        self._log.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        for tag, color in [
            ("ok", C.SUCCESS), ("err", C.ERROR), ("info", C.BLUE),
            ("warn", C.WARNING), ("head", C.PURPLE),
        ]:
            self._log._textbox.tag_configure(tag, foreground=color)

    # helpers
    def _write(self, msg: str, tag: str = ""):
        self._log.configure(state="normal")
        import time as _t
        ts = _t.strftime("%H:%M:%S")
        self._log._textbox.insert("end", f"[{ts}] ", "info")
        self._log._textbox.insert("end", msg + "\n", tag)
        self._log.see("end")
        self._log.configure(state="disabled")

    def _show_recs(self, recs):
        for w in self._rec_widgets:
            w.destroy()
        self._rec_widgets.clear()

        if not recs:
            lbl = ctk.CTkLabel(
                self._rec_list, text="✓ No issues — your setup looks good!",
                font=("Segoe UI", 12), text_color=C.SUCCESS,
            )
            lbl.pack(anchor="w", padx=12, pady=8)
            self._rec_widgets.append(lbl)
            return

        prio_colors = {1: C.ERROR, 2: C.WARNING, 3: C.ORANGE, 4: C.BLUE, 5: C.TEXT_MUTED}
        for r in recs:
            card = ctk.CTkFrame(
                self._rec_list, fg_color=C.BG_RAISED, corner_radius=8,
            )
            card.pack(fill="x", pady=(0, 6), padx=4)
            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(8, 0))
            pc = prio_colors.get(r.priority, C.TEXT_MUTED)
            ctk.CTkLabel(
                top_row, text=f"P{r.priority}", font=("Consolas", 10, "bold"),
                text_color=pc, width=30,
            ).pack(side="left")
            ctk.CTkLabel(
                top_row, text=r.title,
                font=("Segoe UI", 11, "bold"), text_color=C.TEXT,
            ).pack(side="left", padx=(4, 0))
            ctk.CTkLabel(
                card, text=r.detail,
                font=("Segoe UI", 10), text_color=C.TEXT_SEC,
                anchor="w", wraplength=350,
            ).pack(fill="x", padx=14, pady=(2, 8))
            self._rec_widgets.append(card)

    # actions
    def _detect_games(self):
        self._write("Scanning for running games…", "info")
        detected = detect_running_games()
        if detected:
            g = detected[0]
            self.c_game.set(g.display_name, C.PINK)
            self._write(f"Detected: {g.display_name} (PID {g.pid})", "ok")
            Toast(self.app, f"Game detected: {g.display_name}", "success")
        else:
            self.c_game.set("None", C.TEXT_MUTED)
            self._write("No game processes found.", "warn")
            Toast(self.app, "No games detected", "info")

    def _detect_region(self):
        self._write("Detecting region…", "info")
        geo = detect_region()
        self.c_region.set(geo.region_code, C.CYAN)
        self._write(
            f"Region: {geo.region_code} (tz: {geo.timezone}, "
            f"confidence {geo.confidence:.0%})", "ok",
        )
        if geo.confidence < 0.6:
            self._write("Low confidence — running latency test…", "warn")
            self.app.set_status("Latency region detection…")

            def _done(region):
                if isinstance(region, Exception):
                    self.after(0, lambda: self._write(f"Error: {region}", "err"))
                    return
                def _ui():
                    self.c_region.set(region, C.CYAN)
                    self._write(f"Latency region: {region}", "ok")
                    self.app.set_status("Ready")
                self.after(0, _ui)
            _run_async(detect_region_by_latency(), _done)
        else:
            Toast(self.app, f"Region: {geo.region_code}", "success")

    def _assess_net(self):
        self._write("Assessing network condition…", "info")
        self.app.set_status("Assessing network…")

        def _done(cond):
            if isinstance(cond, Exception):
                self.after(0, lambda: self._write(f"Error: {cond}", "err"))
                return
            def _ui():
                qcolors = {
                    "excellent": C.SUCCESS, "good": C.SUCCESS,
                    "fair": C.WARNING, "poor": C.ERROR, "bad": C.ERROR,
                }
                self.c_net.set(cond.quality.upper(), qcolors.get(cond.quality, C.TEXT_MUTED))
                self._write(
                    f"Network: {cond.quality.upper()} — "
                    f"latency {cond.base_latency_ms}ms, jitter {cond.jitter_ms}ms, "
                    f"loss {cond.loss_pct}%", "ok",
                )
                self.app.set_status("Ready")
                Toast(self.app, f"Network: {cond.quality.upper()}", "success")
            self.after(0, _ui)
        _run_async(assess_network(), _done)

    def _run_smart(self):
        self._write("═══ Starting Smart Analysis ═══", "head")
        self.app.set_status("🧠 Smart analysis running…")

        game = self.app.selected_game()
        region = self.app.selected_region()

        def _done(result):
            if isinstance(result, Exception):
                self.after(0, lambda: self._write(f"Error: {result}", "err"))
                self.after(0, lambda: self.app.set_status("Error"))
                return

            def _ui():
                # update cards
                if result.running_game:
                    self.c_game.set(result.running_game.display_name, C.PINK)
                    self._write(f"Game: {result.running_game.display_name}", "ok")

                self.c_region.set(result.region_used, C.CYAN)
                self._write(f"Region: {result.region_used}", "ok")

                if result.network_condition:
                    nc = result.network_condition
                    qcolors = {
                        "excellent": C.SUCCESS, "good": C.SUCCESS,
                        "fair": C.WARNING, "poor": C.ERROR, "bad": C.ERROR,
                    }
                    self.c_net.set(nc.quality.upper(), qcolors.get(nc.quality, C.TEXT_MUTED))
                    self._write(
                        f"Network: {nc.quality.upper()} ({nc.base_latency_ms}ms / "
                        f"jitter {nc.jitter_ms}ms)", "ok",
                    )

                if result.best_server:
                    self.c_server.set(f"{result.best_latency}ms", _ping_color(result.best_latency))
                    flag = " ★ history" if result.history_informed else ""
                    self._write(
                        f"Best: {result.best_server} — {result.best_latency}ms{flag}", "ok",
                    )
                else:
                    self.c_server.set("N/A", C.ERROR)
                    self._write("No reachable server found.", "err")

                if result.ping_strategy:
                    ps = result.ping_strategy
                    self._write(f"Strategy: {ps.reason}", "info")

                self._show_recs(result.recommendations)
                self._write("═══ Smart Analysis Complete ═══", "head")
                self.app.set_status("Smart analysis complete")
                Toast(self.app, "Smart analysis finished!", "success")

            self.after(0, _ui)

        _run_async(smart_select(game, region), _done)


# ─── Main Application ───────────────────────────────────────────────────────

class App(ctk.CTk):
    """Root window – sidebar navigation + swappable content pages."""

    def __init__(self):
        super().__init__()
        self.title("UltimatePing — Gaming Network Optimizer")
        self.geometry("1140x750")
        self.minsize(960, 620)
        self.configure(fg_color=C.BG_ROOT)

        self._build_header()
        self._build_body()
        self._build_status()
        self._build_pages()
        self.navigate("dashboard")

    # ── header ──

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=C.SIDEBAR, corner_radius=0, height=54)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        _logo = _icon("lucide:zap", 22, C.PRIMARY_HOVER)
        if _logo:
            ctk.CTkLabel(hdr, text="", image=_logo).pack(side="left", padx=(20, 6))
        else:
            ctk.CTkLabel(
                hdr, text="⚡", font=("Segoe UI Emoji", 20),
            ).pack(side="left", padx=(20, 6))
        ctk.CTkLabel(
            hdr, text="UltimatePing",
            font=("Segoe UI", 16, "bold"), text_color=C.PRIMARY_HOVER,
        ).pack(side="left")
        ctk.CTkLabel(
            hdr, text="Gaming Network Optimizer",
            font=("Segoe UI", 11), text_color=C.TEXT_MUTED,
        ).pack(side="left", padx=(10, 0))

        if platform.system() == "Windows":
            _gamepad = _icon("lucide:gamepad-2", 14, C.SUCCESS)
            win_lbl = ctk.CTkFrame(hdr, fg_color="transparent")
            win_lbl.pack(side="right", padx=20)
            if _gamepad:
                ctk.CTkLabel(win_lbl, text="", image=_gamepad).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(
                win_lbl, text="Windows Optimized",
                font=("Segoe UI", 10), text_color=C.SUCCESS,
            ).pack(side="left")

        # version badge
        pill = ctk.CTkFrame(hdr, fg_color=C.BG_RAISED, corner_radius=6)
        pill.pack(side="right", padx=10)
        ctk.CTkLabel(
            pill, text="v2.0", font=("Consolas", 10), text_color=C.TEXT_MUTED,
        ).pack(padx=8, pady=2)

    # ── body (sidebar + content) ──

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color=C.BG, corner_radius=0)
        body.pack(fill="both", expand=True)

        self._sidebar = ctk.CTkFrame(
            body, fg_color=C.SIDEBAR, corner_radius=0, width=210,
        )
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # thin separator
        ctk.CTkFrame(
            body, fg_color=C.BORDER, width=1, corner_radius=0,
        ).pack(side="left", fill="y")

        self._content = ctk.CTkFrame(body, fg_color=C.BG, corner_radius=0)
        self._content.pack(side="left", fill="both", expand=True)

        # nav items
        ctk.CTkFrame(self._sidebar, fg_color="transparent", height=10).pack()
        self._nav: Dict[str, NavButton] = {}
        for key, icon, label in [
            ("dashboard", "lucide:layout-dashboard", "Dashboard"),
            ("smart",     "lucide:brain-circuit",    "Smart Mode"),
            ("scanner",   "lucide:radar",            "Server Scanner"),
            ("dns",       "lucide:globe",            "DNS Optimizer"),
            ("monitor",   "lucide:activity",         "Ping Monitor"),
            ("route",     "lucide:route",            "Route Analyzer"),
            ("system",    "lucide:settings",         "System Optimizer"),
            ("sockets",   "lucide:wrench",           "Socket Tuning"),
        ]:
            btn = NavButton(
                self._sidebar, icon, label,
                command=lambda k=key: self.navigate(k),
            )
            btn.pack(fill="x", pady=1)
            self._nav[key] = btn

    # ── status bar ──

    def _build_status(self):
        bar = ctk.CTkFrame(self, fg_color=C.SIDEBAR, corner_radius=0, height=30)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self._status = ctk.CTkLabel(
            bar, text="Ready", font=("Segoe UI", 10),
            text_color=C.TEXT_MUTED, anchor="w",
        )
        self._status.pack(side="left", padx=14, fill="x", expand=True)

        self._ping_lbl = ctk.CTkLabel(
            bar, text="", font=("Consolas", 10), text_color=C.SUCCESS,
        )
        self._ping_lbl.pack(side="right", padx=14)

    def set_status(self, text: str):
        self._status.configure(text=text)

    def set_ping(self, text: str, color: str = C.SUCCESS):
        self._ping_lbl.configure(text=text, text_color=color)

    # ── pages ──

    def _build_pages(self):
        self._pages: Dict[str, ctk.CTkFrame] = {
            "dashboard": DashboardPage(self._content, self),
            "smart":     SmartPage(self._content, self),
            "scanner":   ScannerPage(self._content, self),
            "dns":       DNSPage(self._content, self),
            "monitor":   MonitorPage(self._content, self),
            "route":     RoutePage(self._content, self),
            "system":    SystemPage(self._content, self),
            "sockets":   SocketsPage(self._content, self),
        }
        self._cur: Optional[str] = None

    def navigate(self, key: str):
        # stop monitor if leaving that page
        if self._cur == "monitor" and key != "monitor":
            pg = self._pages.get("monitor")
            if pg and hasattr(pg, "on_leave"):
                pg.on_leave()

        for p in self._pages.values():
            p.pack_forget()
        if key in self._pages:
            self._pages[key].pack(fill="both", expand=True)
            self._cur = key

        for k, btn in self._nav.items():
            btn.set_active(k == key)

    def selected_game(self) -> Optional[str]:
        sc = self._pages.get("scanner")
        return sc.game_key() if sc else None

    def selected_region(self) -> Optional[str]:
        sc = self._pages.get("scanner")
        return sc.region() if sc else None


# ─── Entry Point ─────────────────────────────────────────────────────────────

def launch_gui():
    """Launch the premium GUI."""
    app = App()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
