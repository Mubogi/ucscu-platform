@echo off
REM ---------------------------------------------------------------------------
REM  Make UCSCU Connect start automatically when the Windows server boots.
REM  Registers a Task Scheduler job that runs at system startup as SYSTEM.
REM  Run this once, as Administrator, on the server.
REM ---------------------------------------------------------------------------
setlocal
set TASKNAME=UCSCU Connect Server
set APPDIR=%~dp0
set PYEXE=%APPDIR%.venv\Scripts\python.exe

if not exist "%PYEXE%" set PYEXE=python

echo Registering scheduled task "%TASKNAME%" ...
schtasks /Create /TN "%TASKNAME%" /TR "\"%PYEXE%\" \"%APPDIR%run.py\"" ^
  /SC ONSTART /RU SYSTEM /RL HIGHEST /F

if %ERRORLEVEL% EQU 0 (
  echo.
  echo Done. UCSCU Connect will start automatically after the next boot.
  echo To start it now without rebooting, run:  schtasks /Run /TN "%TASKNAME%"
  echo To remove it later, run:                schtasks /Delete /TN "%TASKNAME%" /F
) else (
  echo.
  echo Could not register the task. Right-click this file and choose
  echo "Run as administrator", then try again.
)
pause
