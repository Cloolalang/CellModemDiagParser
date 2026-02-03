@echo off
REM Install SCAT and all dependencies on Windows.
REM Run this from the scat-master folder, or double-click it.

set "SCATDIR=%~dp0"
if "%SCATDIR:~-1%"=="\" set "SCATDIR=%SCATDIR:~0,-1%"
cd /d "%SCATDIR%"

echo Installing dependencies from requirements.txt...
python -m pip install -r "%SCATDIR%\requirements.txt"
if errorlevel 1 (
    echo Dependencies install failed.
    pause
    exit /b 1
)

echo.
echo Installing SCAT in editable mode...
python -m pip install --editable "%SCATDIR%"
if errorlevel 1 (
    echo Editable install failed. Try: pip install --editable "full-path-to-scat-master"
    pause
    exit /b 1
)

echo.
echo Done. Run scat with: python -m scat -t qc -s COMxx --kpi --dl-bandwidth 20 --json-udp-port 9999
pause
