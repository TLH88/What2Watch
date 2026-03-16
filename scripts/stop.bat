@echo off
REM Stop What2Watch
cd /d "%~dp0\.."
echo Stopping What2Watch...
docker compose down
echo All services stopped.
