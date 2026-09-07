@echo off
REM ============================================================
REM KAUSHALSETU — SETUP SCRIPT (Windows)
REM
REM What to do: double-click this file (setup.bat).
REM If Windows blocks it, right-click it and choose "Run anyway".
REM
REM This installs the two Python packages needed (pandas, numpy)
REM and then builds + opens your dashboard automatically.
REM ============================================================

echo ==========================================
echo  KaushalSetu - Setup
echo ==========================================
echo.
echo [1/2] Installing required packages (pandas, numpy)...
pip install -r requirements.txt

echo.
echo [2/2] Building your dashboard...
python build_and_launch.py

echo.
pause
