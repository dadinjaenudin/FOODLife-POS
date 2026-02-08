@echo off
REM Package POS Launcher Qt for distribution

echo.
echo =============================================================
echo       POS LAUNCHER QT - PACKAGE RELEASE SCRIPT
echo =============================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Step 1: Verify build exists
echo [1/5] Verifying build output...
if not exist "dist\POSLauncher\POSLauncher.exe" (
    echo ERROR: Build not found! Run build_launcher.bat first.
    exit /b 1
)
echo Build found: dist\POSLauncher\POSLauncher.exe
echo.

REM Step 2: Create release directory
echo [2/5] Creating release directory...
if not exist releases mkdir releases

REM Generate version string
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
set RELEASE_NAME=POSLauncher-v%mydate%
set RELEASE_DIR=releases\%RELEASE_NAME%

if exist "%RELEASE_DIR%" (
    rmdir /s /q "%RELEASE_DIR%"
)
mkdir "%RELEASE_DIR%"
echo Created: %RELEASE_DIR%
echo.

REM Step 3: Copy files
echo [3/5] Copying files...
xcopy /E /I /Q dist\POSLauncher "%RELEASE_DIR%"
echo Copied executable and dependencies
echo.

REM Step 4: Create config template and README
echo [4/5] Creating configuration files...

REM Create config.json template
(
echo {
echo   "terminal_code": "BOE-001",
echo   "company_code": "YOGYA",
echo   "brand_code": "BOE",
echo   "store_code": "KPT",
echo   "edge_server": "http://127.0.0.1:8001"
echo }
) > "%RELEASE_DIR%\config.json"
echo Created: config.json

REM Create README.txt
(
echo POS LAUNCHER QT - DEPLOYMENT GUIDE
echo ===================================
echo.
echo CONTENTS:
echo   - POSLauncher.exe       : Main application
echo   - _internal\            : Required libraries
echo   - config.json           : Configuration file
echo   - customer_display.html : Customer display page
echo   - print_monitor.html    : Print monitoring dashboard
echo   - assets\               : Images and resources
echo.
echo INSTALLATION:
echo   1. Extract this folder to target computer
echo   2. Edit config.json:
echo      - terminal_code: Terminal identifier ^(e.g., BOE-001^)
echo      - company_code: Company code ^(e.g., YOGYA^)
echo      - brand_code: Brand code ^(e.g., BOE^)
echo      - store_code: Store code ^(e.g., KPT^)
echo      - edge_server: Django Edge Server URL
echo.
echo CONFIGURATION EXAMPLE:
echo   {
echo       "terminal_code": "BOE-001",
echo       "company_code": "YOGYA",
echo       "brand_code": "BOE",
echo       "store_code": "KPT",
echo       "edge_server": "http://192.168.1.100:8001"
echo   }
echo.
echo   - terminal_code: Unique terminal identifier
echo   - edge_server: URL of Django Edge Server
echo   - Customer display settings managed from database/API
echo.
echo FIRST RUN:
echo   1. Double-click POSLauncher.exe
echo   2. Local API will start on port 5000
echo   3. Browser will open POS interface
echo.
echo PRINTER SETUP:
echo   - Receipt Printer: Configure in Terminal settings
echo   - Windows: Uses win32print ^(default printer^)
echo   - Set printer name in Terminal configuration
echo.
echo CUSTOMER DISPLAY:
echo   - Access: http://localhost:5000/customer-display
echo   - Fullscreen on second monitor recommended
echo   - Auto-refresh enabled
echo.
echo PRINT MONITOR:
echo   - Access: http://localhost:5000/print-monitor
echo   - Monitor print job status
echo   - Retry failed jobs
echo   - Real-time statistics
echo.
echo TROUBLESHOOTING:
echo   - Check launcher_debug.log for errors
echo   - Verify Django server is accessible
echo   - Check firewall settings for port 5000
echo   - Ensure printer is connected and online
echo.
echo SUPPORT:
echo   For issues, check the logs or contact support.
echo.
) > "%RELEASE_DIR%\README.txt"
echo Created: README.txt
echo.

REM Step 5: Create ZIP archive
echo [5/5] Creating ZIP archive...
powershell -command "Compress-Archive -Path '%RELEASE_DIR%\*' -DestinationPath 'releases\%RELEASE_NAME%.zip' -Force"
if %ERRORLEVEL% EQU 0 (
    echo Created: releases\%RELEASE_NAME%.zip
    
    REM Get ZIP file size
    for %%A in ("releases\%RELEASE_NAME%.zip") do (
        set /a size_mb=%%~zA/1048576
    )
    echo Size: !size_mb! MB
) else (
    echo WARNING: Could not create ZIP archive
    echo You can manually ZIP the folder: %RELEASE_DIR%
)
echo.

REM Success summary
echo.
echo =============================================================
echo              PACKAGING COMPLETE!
echo =============================================================
echo.
echo Release Package:
echo   releases\%RELEASE_NAME%.zip
echo.
echo Folder Contents:
echo   releases\%RELEASE_NAME%\
echo.
echo Deployment Steps:
echo   1. Transfer ZIP to target computer
echo   2. Extract ZIP file
echo   3. Edit config.json with server URL
echo   4. Run POSLauncher.exe
echo.
echo Ready for deployment!
echo.
