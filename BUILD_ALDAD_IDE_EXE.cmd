@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ==========================================
echo       ALDAD IDE 1.9.17 - BUILD EXE
echo ==========================================
echo.

set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY (where python >nul 2>nul && set PY=python)
if not defined PY (
  echo [ERROR] Python was not found.
  echo Run REPAIR_ALDAD.cmd first.
  pause
  exit /b 1
)

echo [1/4] Installing PyInstaller...
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 goto FAIL

if exist build_exe rmdir /s /q build_exe
if exist dist_exe rmdir /s /q dist_exe
mkdir build_exe
mkdir dist_exe

echo [2/4] Building DadRunner.exe...
%PY% -m PyInstaller --noconfirm --clean --onefile --console ^
  --name DadRunner ^
  --distpath "%CD%\build_exe\runner_dist" ^
  --workpath "%CD%\build_exe\runner_work" ^
  --specpath "%CD%\build_exe\runner_spec" ^
  --paths "%CD%" ^
  --hidden-import ui --hidden-import vnext --hidden-import aldad_syntax --hidden-import aldad_runtime ^
  "%CD%\dad.py"
if errorlevel 1 goto FAIL
if not exist "%CD%\build_exe\runner_dist\DadRunner.exe" goto FAIL

echo [3/4] Building Aldad_IDE_1.9.17.exe...
%PY% -m PyInstaller --noconfirm --clean --onefile --noconsole ^
  --name Aldad_IDE_1.9.17 ^
  --distpath "%CD%\dist_exe" ^
  --workpath "%CD%\build_exe\ide_work" ^
  --specpath "%CD%\build_exe\ide_spec" ^
  --add-binary "%CD%\build_exe\runner_dist\DadRunner.exe;." ^
  --add-data "%CD%\rules_ar.md;." ^
  --add-data "%CD%\example.dad;." ^
  --add-data "%CD%\aldad_ide_pro.dad;." ^
  "%CD%\aldad_ide.py"
if errorlevel 1 goto FAIL
if not exist "%CD%\dist_exe\Aldad_IDE_1.9.17.exe" goto FAIL

echo [4/4] Done.
copy /y "%CD%\dist_exe\Aldad_IDE_1.9.17.exe" "%CD%\Aldad_IDE_1.9.17.exe" >nul
echo.
echo [OK] EXE created:
echo %CD%\Aldad_IDE_1.9.17.exe
echo.
echo You can run this EXE without installing Python on the target PC.
pause
exit /b 0

:FAIL
echo.
echo [ERROR] EXE build failed.
echo Send a screenshot of this window for diagnosis.
pause
exit /b 1
