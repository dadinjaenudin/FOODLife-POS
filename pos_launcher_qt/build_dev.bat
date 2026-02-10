@echo off
REM Build POS Launcher Qt - DEVELOPMENT BUILD
REM For quick testing and development purposes only
REM Requirements: Python 3.8+, PyInstaller

echo.
echo =============================================================
echo       POS LAUNCHER QT - DEVELOPMENT BUILD
echo =============================================================
echo.
echo For quick testing only - does NOT create release package
echo For production release, use: build_prod.bat
echo.
echo ⚠ IMPORTANT: Close all File Explorer windows before building!
echo   If build fails with "file is being used", run: close_explorer.bat
echo.

REM Step 1: Verify Python installation
echo [1/8] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found! Please install Python 3.8+
    exit /b 1
)
python --version
echo.

REM Step 2: Change to script directory
echo [2/8] Setting up build environment...
cd /d "%~dp0"
echo Working directory: %CD%
echo.

REM Step 3: Install dependencies
echo [3/8] Installing dependencies...
if exist requirements.txt (
    echo Installing from requirements.txt...
    python -m pip install --upgrade pip --quiet
    python -m pip install -r requirements.txt --quiet
    echo Dependencies installed!
) else (
    echo WARNING: requirements.txt not found!
)
echo.

REM Step 4: Install PyInstaller
echo [4/8] Installing PyInstaller (compatible version)...
python -m pip install pyinstaller==6.3.0 --quiet
echo PyInstaller 6.3.0 installed!
echo.

REM Step 5: Kill running processes to avoid file locks
echo [5/9] Killing any running POS Launcher processes...

REM Kill POSLauncher.exe
taskkill /F /IM POSLauncher.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Killed POSLauncher.exe process
    timeout /t 1 /nobreak >nul
) else (
    echo   No POSLauncher.exe process found (OK)
)

REM Kill any Python processes running pos_launcher_qt.py
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH 2^>nul ^| findstr /I "pos_launcher"') do (
    echo ✓ Killing Python PID: %%~a
    taskkill /F /PID %%~a >nul 2>&1
)

REM Check if any handles on dist folder
if exist dist (
    echo Checking for file locks on dist\ folder...
    handle "dist\POSLauncher" >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo WARNING: Handle.exe not found, can't check for locks
    )
)

REM Wait for processes to fully terminate and release file handles
echo Waiting for processes to release file handles...
timeout /t 3 /nobreak >nul
echo Process cleanup complete!
echo.

REM Step 6: Clean previous build
echo [6/9] Cleaning previous build artifacts...

REM Delete build directory
if exist build (
    echo Removing build\ directory...
    rmdir /s /q build 2>nul
    if exist build (
        timeout /t 1 /nobreak >nul
        rmdir /s /q build 2>nul
    )
    if not exist build (
        echo ✓ Removed build\ directory
    )
)


REM Step 7: Run PyInstaller
echo [7/9] Building executable with PyInstaller...
echo.
echo =============================================================
echo              PYINSTALLER BUILD OUTPUT
echo =============================================================
echo.

REM Build WITHOUT --clean flag (we already cleaned manually)
python -m PyInstaller pos_launcher.spec --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Build failed! Check the output above for errors.
    exit /b 1
)

echo.
echo Build completed successfully!
echo.

REM Clean up old dist_old folder after successful build
if exist dist_old (
    echo Removing old dist_old\ folder...
    rmdir /s /q dist_old 2>nul
    if not exist dist_old (
        echo ✓ Cleaned up old build artifacts
    )
)
echo.

REM Step 8: Copy config files to dist
echo [8/9] Copying config files to dist...
if exist config.json (
    copy /Y config.json dist\POSLauncher\ >nul
    echo ✓ Copied config.json
) else (
    echo WARNING: config.json not found
)
echo.

REM Step 9: Verify build output
echo [9/9] Verifying build output...
if exist "dist\POSLauncher\POSLauncher.exe" (
    echo Executable created: dist\POSLauncher\POSLauncher.exe
    for %%A in ("dist\POSLauncher\POSLauncher.exe") do echo Size: %%~zA bytes
    echo.
) else (
    echo ERROR: Executable not found at: dist\POSLauncher\POSLauncher.exe
    exit /b 1
)

REM Success summary
echo.
echo =============================================================
echo                  BUILD SUCCESSFUL!
echo =============================================================
echo.
echo Output Location:
echo   dist\POSLauncher\
echo.
echo Executable:
echo   dist\POSLauncher\POSLauncher.exe
echo.
echo Next Steps:
echo   1. Test the executable locally:
echo      cd dist\POSLauncher
echo      POSLauncher.exe
echo.
echo   2. Package for distribution:
echo      package_release.bat
echo.
echo   3. Deploy to target computer:
echo      - Copy entire POSLauncher folder
echo      - Run POSLauncher.exe
echo.
