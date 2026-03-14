@echo off
echo ============================================================
echo IntelliKnow KMS - Cloudflare Tunnel Launcher
echo ============================================================
echo.

echo Step 1: Checking if backend is running...
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Backend may not be running on port 8000
    echo.
    echo Please start backend first:
    echo   uvicorn backend.main:app --reload --port 8000
    echo.
    pause
    exit /b 1
)

echo [OK] Backend is running on port 8000
echo.

echo Step 2: Starting Cloudflare Tunnel...
echo.
echo IMPORTANT: Copy the HTTPS URL when cloudflared starts
echo Use it to configure Bot webhook endpoints
echo.
echo Webhook URLs:
echo   - Teams:    https://your-url.trycloudflare.com/api/bot/teams/webhook
echo   - Telegram: https://your-url.trycloudflare.com/api/bot/telegram/webhook
echo   - DingTalk: https://your-url.trycloudflare.com/webhook/dingtalk
echo.
echo ============================================================
echo.

cloudflared tunnel --url http://localhost:8000

echo.
echo ============================================================
echo Cloudflare tunnel stopped
echo ============================================================
pause
