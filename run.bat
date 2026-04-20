@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "venv\Scripts\activate.bat" (
    echo Run setup.bat first.
    exit /b 1
)
call "%~dp0venv\Scripts\activate.bat"
python app.py %*
set EXITCODE=%ERRORLEVEL%
exit /b %EXITCODE%
