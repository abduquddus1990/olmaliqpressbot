@echo off
chcp 65001 > nul
setlocal

set "TASK_NAME=OlmaliqpressBotService"
set "SCRIPT_PATH=%~dp0run_silent.vbs"

echo ================================================================
echo   OLMALIQPRESS BOT - Windows Orqa Fonda 24/7 Avtomatik Ishlash
echo ================================================================
echo.

schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [!] Eski servis topildi. O'chirilmoqda...
    schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
)

echo [*] Yangi avtomatik Task yaratilmoqda...
schtasks /create /tn "%TASK_NAME%" /tr "wscript.exe \"%SCRIPT_PATH%\"" /sc onlogon /rl highest /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo [OK] Servis muvaffaqiyatli o'rnatildi!
    echo [*] Bot hoziroq orqa fonda ishga tushirilmoqda...
    schtasks /run /tn "%TASK_NAME%"
    echo.
    echo ================================================================
    echo  BOT HOZIR FONDA ISHLAMOQDA!
    echo  Kompyuteringiz har gal yoqilganda o'zi avtomatik ishga tushadi.
    echo  To'xtatish uchun: stop_service.bat ni bosing.
    echo ================================================================
) else (
    echo.
    echo [XATO] Administrator ruxsati kerak bo'lishi mumkin.
    echo Iltimos, ushbu faylni "Run as Administrator" qilib bosing.
)

pause
