@echo off
title Swdbot Telegram - Local Dev
set DB_PATH=data\bot_local.db
echo ========================================
echo   Swdbot Telegram - Local Development
echo   Dashboard: http://localhost:8080/admin
echo   Bot: @Viintools (polling mode)
echo   Tekan CTRL+C untuk berhenti
echo ========================================
python bot.py
pause
