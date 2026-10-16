@echo off
setlocal
cd /d "%~dp0"
echo.
echo ===================================================
echo   PO INTELLIGENCE HUB v1.9.3 - EVIDENCE-BASED ANSWERS
echo ===================================================
echo.
if exist "runtime\python.exe" (
    "runtime\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 goto bundled
)
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 goto launcher
)
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 goto python
)
echo [ERROR] Python 3.10 or newer is required.
echo Install Python from python.org and enable Add Python to PATH.
pause
exit /b 1
:bundled
"runtime\python.exe" server.py
goto done
:launcher
py -3 server.py
goto done
:python
python server.py
:done
echo.
echo Server stopped. See any error above before closing.
pause
endlocal
