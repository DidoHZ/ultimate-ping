@echo off
:: ═══════════════════════════════════════════════════════════════
::  UltimatePing — Windows Build Script
::  Produces: dist\UltimatePing.exe  (single-file, GUI, no console)
:: ═══════════════════════════════════════════════════════════════
title UltimatePing Builder

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   UltimatePing — Windows EXE Builder     ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ── 1. check Python ──
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)
echo  [OK] Python found

:: ── 2. create/activate venv ──
if not exist ".venv" (
    echo  [..] Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo  [OK] Virtual environment activated

:: ── 3. install dependencies ──
echo  [..] Installing dependencies...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1
pip install pyinstaller >nul 2>&1
echo  [OK] Dependencies installed

:: ── 4. build ──
echo  [..] Building UltimatePing.exe ...
echo.
pyinstaller ultimateping.spec --noconfirm --clean
echo.

if exist "dist\UltimatePing.exe" (
    echo  ═══════════════════════════════════════════
    echo   BUILD SUCCESSFUL!
    echo   Output: dist\UltimatePing.exe
    echo  ═══════════════════════════════════════════
    echo.
    echo  You can now copy dist\UltimatePing.exe anywhere and run it.
) else (
    echo  [ERROR] Build failed — check the output above.
)

echo.
pause
