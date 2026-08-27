@echo off
chcp 65001 > nul
setlocal

set "TASK_NAME=OlmaliqpressBotService"

echo ================================================================
echo   OLMALIQPRESS BOT - Servisni To'xtatish
echo ================================================================
echo.

schtasks /end /tn "%TASK_NAME%" >nul 2>&1
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

taskkill /F /IM python.exe /FI "WINDOWTITLE eq Olmaliqpress*" >nul 2>&1

echo [OK] Bot va uning avtomatik servisi to'xtatildi hamda o'chirildi.
pause
