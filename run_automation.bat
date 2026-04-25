@echo off
title TikTok Ads Automation
echo =======================================
echo   Starting TikTok Ads Automation...
echo =======================================
python main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo Script crashed or was stopped with an error.
)
pause
