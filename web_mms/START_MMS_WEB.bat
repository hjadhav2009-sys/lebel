@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
  echo Docker Desktop is required to start PostgreSQL and the backend.
  echo Install Docker Desktop, then run this file again.
  pause
  exit /b 1
)

where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo Node.js is required to start the MMS web interface.
  pause
  exit /b 1
)

docker compose up -d --build db backend
if errorlevel 1 exit /b 1

if not exist "frontend\node_modules" call npm.cmd --prefix frontend install
start "MMS Web Frontend" /min cmd /c "npm.cmd --prefix frontend run dev"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddMinutes(2); do { try { $r=Invoke-RestMethod http://localhost:8000/health -TimeoutSec 2; if ($r.status -eq 'ok') { Start-Process http://localhost:5173; exit 0 } } catch {}; Start-Sleep -Seconds 2 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 echo Backend health check timed out. Run docker compose logs backend for details.
endlocal
