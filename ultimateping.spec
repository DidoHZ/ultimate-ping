# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for UltimatePing — Gaming Network Optimizer
Cross-platform: produces .exe on Windows, .app on macOS.

  Windows:  pyinstaller ultimateping.spec
  macOS:    pyinstaller ultimateping.spec
"""

import os
import sys
import platform
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
IS_MAC = platform.system() == "Darwin"

# Collect customtkinter assets (themes, fonts etc.)
ctk_data = collect_data_files("customtkinter")

# Pick the right icon format
if IS_MAC and os.path.exists("icon.icns"):
    app_icon = "icon.icns"
elif os.path.exists("icon.ico"):
    app_icon = "icon.ico"
else:
    app_icon = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=ctk_data,
    hiddenimports=[
        "customtkinter",
        "gui",
        "intelligence",
        "config",
        "network_scanner",
        "route_optimizer",
        "dns_optimizer",
        "tcp_udp_tuner",
        "ping_monitor",
        "os_optimizer",
        "statistics",
    ] + collect_submodules("customtkinter"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "scipy", "pandas", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if IS_MAC:
    # ── macOS: onedir mode → .app bundle ──
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="UltimatePing",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=app_icon,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="UltimatePing",
    )
    app = BUNDLE(
        coll,
        name="UltimatePing.app",
        icon=app_icon,
        bundle_identifier="com.ultimateping.app",
        info_plist={
            "CFBundleDisplayName": "UltimatePing",
            "CFBundleShortVersionString": "2.0.0",
            "CFBundleVersion": "2.0.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "10.15",
        },
    )
else:
    # ── Windows: single-file .exe ──
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="UltimatePing",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        icon=app_icon,
    )
