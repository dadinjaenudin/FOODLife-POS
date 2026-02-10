@echo off
REM Force Kill File Explorer accessing dist folder

echo ============================================================
echo  FORCE CLOSE FILE EXPLORERWINDOWS
echo ============================================================
echo.

echo Killing all Windows Explorer processes...
echo.

REM Close all Windows Explorer windows
taskkill /F /IM explorer.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Killed all Explorer windows
) else (
    echo   No Explorer process found
)

REM Wait for Explorer to fully close
timeout /t 2 /nobreak >nul

REM Restart Explorer
echo.
echo Restarting Windows Explorer...
start explorer.exe

echo.
echo ✓ Done! File Explorer restarted
echo   You can now run build_dev.bat
echo.
pause
