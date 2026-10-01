@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ======================================
echo        ALDAD 1.9.17 - START
echo ======================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,9) else 1)" >nul 2>nul
  if %errorlevel%==0 goto RUN_PY
)

where python >nul 2>nul
if %errorlevel%==0 (
  python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,9) else 1)" >nul 2>nul
  if %errorlevel%==0 goto RUN_PYTHON
)

where python3 >nul 2>nul
if %errorlevel%==0 (
  python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,9) else 1)" >nul 2>nul
  if %errorlevel%==0 goto RUN_PYTHON3
)

echo [ERROR] Python 3.9 or newer was not found.
echo Run REPAIR_ALDAD.cmd from this same folder.
pause
exit /b 1

:RUN_PY
echo [OK] Starting Aldad...
py -3 "%~dp0aldad_ide.py"
set RC=%errorlevel%
goto END

:RUN_PYTHON
echo [OK] Starting Aldad...
python "%~dp0aldad_ide.py"
set RC=%errorlevel%
goto END

:RUN_PYTHON3
echo [OK] Starting Aldad...
python3 "%~dp0aldad_ide.py"
set RC=%errorlevel%

:END
if not "%RC%"=="0" (
  echo.
  echo [ERROR] Aldad stopped with code %RC%.
  echo Run REPAIR_ALDAD.cmd and send a screenshot if it still fails.
  pause
)
exit /b %RC%
