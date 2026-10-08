@echo off
REM ---------------------------------------------------------------------------
REM  Start UCSCU Connect on the office server.
REM  It listens on 0.0.0.0:12000 and prints the LAN address + QR code to connect.
REM ---------------------------------------------------------------------------
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

set PORT=12000
echo Starting UCSCU Connect on port %PORT% ...
python run.py
pause
