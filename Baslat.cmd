@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python bulunamadi. README.md dosyasindaki Python kurulumunu tamamlayin.
  pause
  exit /b 1
)
py -3 yama.py --gui
if errorlevel 1 (
  echo Arac acilamadi. Once: py -3 -m pip install -r requirements.txt
  pause
  exit /b 1
)
