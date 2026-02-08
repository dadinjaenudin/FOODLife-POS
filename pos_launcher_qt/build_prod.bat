@echo off
REM Build POS Launcher Qt - PRODUCTION RELEASE
REM One-click script to build and package for deployment
REM Creates ZIP file ready for customer distribution

echo.
echo =============================================================
echo       POS LAUNCHER QT - PRODUCTION BUILD
echo =============================================================
echo.
echo This script will:
echo   1. Verify Python installation
echo   2. Install dependencies
echo   3. Build executable with PyInstaller
echo   4. Package into distributable ZIP for deployment
echo.

REM Record start time
set START_TIME=%TIME%

REM Change to script directory
cd /d "%~dp0"

REM Step 0: Check Python
echo =============================================================
echo   STEP 0: VERIFYING PYTHON INSTALLATION
echo =============================================================
echo.
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found! Please install Python 3.8+
    exit /b 1
)
python --version
echo Python OK!
echo.

REM Step 1: Fix dependencies
echo =============================================================
echo   STEP 1: INSTALLING DEPENDENCIES
echo =============================================================
echo.

REM Install all dependencies from requirements.txt (includes correct PyQt6 versions)
echo Installing dependencies from requirements.txt...
python -m pip install -q -r requirements.txt

echo ✓ Dependencies installed!
echo.

REM Step 2: Build
echo =============================================================
echo   STEP 2: BUILDING EXECUTABLE
echo =============================================================
echo.

call build_dev.bat
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Build failed!
    exit /b 1
)

REM Step 3: Package
echo.
echo.
echo =============================================================
echo   STEP 3: PACKAGING RELEASE
echo =============================================================
echo.

call package_release.bat
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Packaging failed!
    exit /b 1
)

REM Calculate duration
set END_TIME=%TIME%

REM Final summary
echo.
echo.
echo =============================================================
echo             ALL DONE! READY FOR DEPLOYMENT
echo =============================================================
echo.
echo Build Time: Started at %START_TIME%, Ended at %END_TIME%
echo.

REM Find latest ZIP
for /f "delims=" %%A in ('dir /b /o-d releases\*.zip 2^>nul') do (
    set LATEST_ZIP=%%A
    goto :found
)
:found

if defined LATEST_ZIP (
    echo Release Package Location:
    echo   releases\%LATEST_ZIP%
    for %%A in ("releases\%LATEST_ZIP%") do (
        set /a size_mb=%%~zA/1048576
    )
    echo   Size: !size_mb! MB
) else (
    echo WARNING: ZIP file not found in releases folder
)

echo.
echo Next Steps:
echo   1. Test locally: cd releases\POSLauncher-v* ^&^& POSLauncher.exe
echo   2. Transfer ZIP to target computer
echo   3. Extract and configure config.json
echo   4. Run POSLauncher.exe
echo.
