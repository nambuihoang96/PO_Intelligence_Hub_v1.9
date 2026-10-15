@echo off
setlocal
cd /d "%~dp0"
echo This optionally installs google-play-scraper from PyPI.
echo It is an UNOFFICIAL third-party connector, NOT an official Google API.
echo It may break or be rate-limited. Review store rules and your organization's policy.
echo No paid API is used. This installs software on your local Python environment.
choice /C YN /M "Install optional connector?"
if errorlevel 2 exit /b 0
if exist "runtime\python.exe" (
  "runtime\python.exe" -m ensurepip --upgrade
  if errorlevel 1 goto failed
  "runtime\python.exe" -m pip install google-play-scraper
  if errorlevel 1 goto failed
  goto installed
)
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m pip install google-play-scraper
) else (
  python -m pip install google-play-scraper
)
if errorlevel 1 goto failed
:installed
echo Installed. Restart RUN_WINDOWS.bat
goto done
:failed
echo Install failed. See the error above.
:done
pause
endlocal
