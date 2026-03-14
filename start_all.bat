@echo off
echo ============================================================
echo IntelliKnow KMS - Complete Startup Script
echo ============================================================
echo.
echo This script will:
echo   1. Start Backend Server (FastAPI)
echo   2. Start Admin UI (Streamlit)
echo   3. Start Cloudflare Tunnel (for Bot testing)
echo.
echo ============================================================
pause

echo.
echo [1/3] Starting Backend Server...
cd /d "%~dp0"
start "IntelliKnow Backend" python backend/main.py
timeout /t 3 >nul

echo.
echo [2/3] Starting Admin UI...
start "IntelliKnow Admin UI" streamlit run frontend/app.py
timeout /t 3 >nul

echo.
echo [3/3] Starting Cloudflare Tunnel...
echo.
echo ============================================================
echo Cloudflare Tunnel is starting...
echo.
echo IMPORTANT ACTIONS:
echo   1. Wait for cloudflared to show the HTTPS URL
echo   2. Copy the HTTPS URL (e.g., https://abc123.trycloudflare.com)
echo   3. Use this URL for Bot webhook configuration:
echo      Telegram:  [COPIED-URL]/api/bot/telegram/webhook
echo      DingTalk: [COPIED-URL]/api/bot/dingtalk/webhook
echo      Teams:     [COPIED-URL]/api/bot/teams/webhook
echo      Feishu:    [COPIED-URL]/api/bot/feishu/webhook
echo.
echo ============================================================
echo.

.\cloudflared.exe tunnel --url http://localhost:8000

pause
