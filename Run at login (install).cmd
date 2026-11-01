@echo off
chcp 65001 >nul
rem Lance Surface Control en arrière-plan (sans fenêtre) à chaque ouverture de session.
cd /d "%~dp0"
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Surface Control.lnk"
powershell -NoProfile -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:LINK); $s.TargetPath = (Get-Command pyw.exe).Source; $s.Arguments = '\"%~dp0server\main.py\"'; $s.WorkingDirectory = '%~dp0'; $s.Save()"
if errorlevel 1 (
  echo Impossible de créer le raccourci de démarrage.
) else (
  echo Surface Control démarrera automatiquement à l'ouverture de session.
  echo Le code PIN est affiché dans Réglages en ouvrant http://localhost:8765 sur ce PC.
)
pause
