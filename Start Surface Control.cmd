@echo off
chcp 65001 >nul
title Surface Control
cd /d "%~dp0"

set "PY=python"
where py >nul 2>nul && set "PY=py -3"

%PY% -c "import psutil" 2>nul || (
  echo Installation du paquet psutil...
  %PY% -m pip install --user psutil || goto :fail
)

rem Optionnel : la barre de lecture (titre et position du morceau en cours).
%PY% -c "import winrt.windows.media.control" 2>nul || (
  echo Installation des paquets winrt pour la barre de lecture...
  %PY% -m pip install --user winrt-runtime winrt-Windows.Media.Control winrt-Windows.Foundation
)

%PY% server\main.py %*
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo Surface Control s'est arrêté sur une erreur. Détails dans data\server.log
pause
