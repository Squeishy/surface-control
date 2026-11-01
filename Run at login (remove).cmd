@echo off
chcp 65001 >nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Surface Control.lnk" 2>nul && (
  echo Surface Control ne démarre plus à l'ouverture de session.
) || (
  echo Il n'était pas configuré pour démarrer à l'ouverture de session.
)
pause
