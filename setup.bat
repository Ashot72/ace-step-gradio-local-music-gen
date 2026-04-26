@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ACESTEP_PIP_SPEC=ace-step @ git+https://github.com/ace-step/ACE-Step-1.5.git"

echo.
echo === music-gen setup ===
where python >nul 2>&1
if errorlevel 1 (
    echo Python not on PATH. Install Python 3.11+ and retry.
    exit /b 1
)
if not exist "venv\Scripts\activate.bat" (
    echo [1/6] Creating venv
    python -m venv venv
    if errorlevel 1 exit /b 1
) else (
    echo [1/6] Using existing venv
)
call "%~dp0venv\Scripts\activate.bat"
echo [2/6] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
echo [3/6] requirements.txt
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo python -m pip install failed.
    exit /b 1
)
echo.
echo [4/6] ace-step --no-deps
python -m pip install "%ACESTEP_PIP_SPEC%" --no-deps
if errorlevel 1 (
    echo ace-step install failed.
    exit /b 1
)
echo [5/6] XPU check
python "%~dp0verify_xpu.py"
if errorlevel 1 (
    echo XPU check failed.
)
echo.
python -c "import acestep; print('ace-step OK')" 2>nul
if errorlevel 1 (
    echo ace-step import failed.
    exit /b 1
)
set "ACESTEP_PROJECT_ROOT=%cd%"
echo [6/6] Checkpoints - turbo (main) model bundle
python -m acestep.model_downloader --model main
if errorlevel 1 (
    echo Checkpoint download failed.
    exit /b 1
)
echo Done. Run run.bat
exit /b 0
