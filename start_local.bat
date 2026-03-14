@echo off
echo ============================================================
echo IntelliKnow KMS - Local Startup Script (No Cloudflare)
echo ============================================================
echo.
echo This script will:
echo   1. Start Backend Server (FastAPI) on port 8000
echo   2. Start Admin UI (Streamlit) on port 8501
echo.
echo Access URLs:
echo   - Backend API:  http://localhost:8000
echo   - Admin UI:     http://localhost:8501
echo   - API Docs:     http://localhost:8000/docs
echo.
echo Note: For Bot integration, you'll need to use Cloudflare Tunnel
echo       or another tunneling service to expose localhost.
echo       See INSTALL_CLOUDFLARED.md for instructions.
echo ============================================================
pause

echo.
echo [1/2] Starting Backend Server...
cd /d "%~dp0"
start "IntelliKnow Backend" python backend/main.py
timeout /t 3 >nul

echo.
echo [2/2] Starting Admin UI...
start "IntelliKnow Admin UI" streamlit run frontend/app.py
timeout /t 2 >nul

echo.
echo ============================================================
echo Services Started!
echo ============================================================
echo.
echo Backend:  http://localhost:8000
echo Admin UI: http://localhost:8501
echo.
echo Press Ctrl+C in each window to stop services.
echo ============================================================
echo.
pause
