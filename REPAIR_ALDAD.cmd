@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ======================================
echo       ALDAD 1.9 - CHECK/REPAIR
echo ======================================
echo Folder: %CD%
echo.

if not exist "dad.py" echo [ERROR] dad.py is missing
if not exist "vnext.py" echo [ERROR] vnext.py is missing
if not exist "aldad_syntax.py" echo [ERROR] aldad_syntax.py is missing
if not exist "aldad_runtime.py" echo [ERROR] aldad_runtime.py is missing
if not exist "aldad_ide.py" echo [ERROR] aldad_ide.py is missing
if not exist "example.dad" echo [ERROR] example.dad is missing

set FOUND=
where py >nul 2>nul && set FOUND=py -3
if not defined FOUND (where python >nul 2>nul && set FOUND=python)
if not defined FOUND (where python3 >nul 2>nul && set FOUND=python3)
if defined FOUND goto TEST

echo [ERROR] Python was not found.
where winget >nul 2>nul
if errorlevel 1 goto NOWINGET
choice /C YN /N /M "Install Python 3.13 with winget now? [Y/N]: "
if errorlevel 2 goto END
winget install -e --id Python.Python.3.13 --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo [ERROR] Python install failed.
  goto END
)
echo [OK] Python installed. Close this window and run START_ALDAD.cmd.
goto END

:NOWINGET
echo [ERROR] winget is not available. Install Python 3.13 from python.org.
goto END

:TEST
echo [OK] Python found: %FOUND%
%FOUND% --version
echo.
echo Testing Aldad engine...
%FOUND% dad.py run example.dad
if errorlevel 1 (
  echo.
  echo [ERROR] Engine test failed.
  goto END
)
echo.
echo [OK] Engine test passed.
echo Starting IDE...
%FOUND% aldad_ide.py

:END
echo.
pause
