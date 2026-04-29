@echo off
setlocal enabledelayedexpansion
title FL Studio Producer Brain — Installer

echo.
echo  =====================================================
echo   FL Studio Producer Brain — MCP Server Installer
echo  =====================================================
echo.

:: ── 1. Check Python 3.11+ ────────────────────────────────────────────────────
echo [1/6] Checking Python version...

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python is not installed or not in PATH.
    echo  Download Python 3.11+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set PYMAJ=%%a
    set PYMIN=%%b
)

if !PYMAJ! LSS 3 (
    echo  ERROR: Python 3.11+ required. Found: !PYVER!
    pause
    exit /b 1
)
if !PYMAJ! EQU 3 if !PYMIN! LSS 11 (
    echo  ERROR: Python 3.11+ required. Found: !PYVER!
    pause
    exit /b 1
)

echo  OK — Python !PYVER! found.

:: ── 2. Create virtualenv ─────────────────────────────────────────────────────
echo.
echo [2/6] Creating virtual environment...

if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  Virtual environment created.
) else (
    echo  Virtual environment already exists — skipping.
)

:: ── 3. Install dependencies ──────────────────────────────────────────────────
echo.
echo [3/6] Installing dependencies (this may take a few minutes)...

call venv\Scripts\activate.bat
pip install --upgrade pip --quiet
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo  ERROR: Some packages failed to install.
    echo  Common issues:
    echo    - python-rtmidi needs Microsoft C++ Build Tools on some systems.
    echo      Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo    - librosa needs soundfile which needs libsndfile.
    echo  Try running: pip install -r requirements.txt  manually for details.
    pause
    exit /b 1
)
echo  Dependencies installed.

:: ── 4. Copy config if missing ────────────────────────────────────────────────
echo.
echo [4/6] Setting up config.json...

if not exist "config.json" (
    copy "config.example.json" "config.json" >nul
    echo  config.json created from template.
) else (
    echo  config.json already exists — skipping.
)

:: ── 5. Auto-detect FL Studio folder ─────────────────────────────────────────
echo.
echo [5/6] Auto-detecting FL Studio installation...

set "FL_USER_DATA=%USERPROFILE%\Documents\Image-Line\FL Studio"
set "FL_INSTALL_24=C:\Program Files\Image-Line\FL Studio 2024"
set "FL_INSTALL_21=C:\Program Files\Image-Line\FL Studio 21"
set "FL_INSTALL_20=C:\Program Files\Image-Line\FL Studio 20"

set "FL_FOUND=0"
if exist "!FL_USER_DATA!" (
    set "FL_FOUND=1"
    echo  Found FL Studio user data: !FL_USER_DATA!
)

:: Update config.json with actual username
:: Write the helper script to a temp file to avoid quoting issues inside python -c
echo import json, os, pathlib > _setup_config.py
echo config_path = pathlib.Path('config.json') >> _setup_config.py
echo text = config_path.read_text(encoding='utf-8') >> _setup_config.py
echo text = text.replace('{USER}', os.environ.get('USERNAME', 'User')) >> _setup_config.py
echo cfg = json.loads(text) >> _setup_config.py
echo fl_data = os.path.join(os.environ.get('USERPROFILE',''), 'Documents', 'Image-Line', 'FL Studio') >> _setup_config.py
echo if pathlib.Path(fl_data).exists(): >> _setup_config.py
echo     cfg['fl_studio']['user_data_folder'] = fl_data >> _setup_config.py
echo samples_default = os.path.join(os.environ.get('USERPROFILE',''), 'Music', 'Samples') >> _setup_config.py
echo cfg['samples']['scan_folders'] = [samples_default] >> _setup_config.py
echo config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8') >> _setup_config.py
echo print('  config.json updated with your user paths.') >> _setup_config.py

python _setup_config.py
del _setup_config.py

if !FL_FOUND! EQU 0 (
    echo  WARNING: FL Studio user data folder not found at default location.
    echo  Edit config.json and set fl_studio.user_data_folder to your actual path.
)

:: ── 6. Print connection instructions ─────────────────────────────────────────
echo.
echo [6/6] Setup complete!
echo.
echo  =====================================================
echo   HOW TO CONNECT TO CLAUDE
echo  =====================================================
echo.
echo  Get the full path to server.py:
echo    %CD%\server.py
echo.
echo  --- Claude Desktop ---
echo  Edit %%APPDATA%%\Claude\claude_desktop_config.json and add:
echo.
echo  {
echo    "mcpServers": {
echo      "fl-studio-producer-brain": {
echo        "command": "%CD%\venv\Scripts\python.exe",
echo        "args": ["%CD%\server.py"]
echo      }
echo    }
echo  }
echo.
echo  --- Claude Code (CLI) ---
echo  Run this command once:
echo.
echo    claude mcp add fl-studio-producer-brain "%CD%\venv\Scripts\python.exe" "%CD%\server.py"
echo.
echo  Or add to .claude/mcp.json in your project:
echo.
echo  {
echo    "mcpServers": {
echo      "fl-studio-producer-brain": {
echo        "command": "%CD%\venv\Scripts\python.exe",
echo        "args": ["%CD%\server.py"]
echo      }
echo    }
echo  }
echo.
echo  =====================================================
echo   REQUIREMENTS
echo  =====================================================
echo   - LoopMIDI: https://www.tobias-erichsen.de/software/loopmidi.html
echo     Create a virtual port named "loopMIDI Port"
echo     In FL Studio: Options > MIDI > enable the LoopMIDI input
echo  =====================================================
echo.
echo  Press any key to exit...
pause >nul
endlocal
