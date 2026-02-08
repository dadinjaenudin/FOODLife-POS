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

REM Step 5: Clean previous build
echo [5/8] Cleaning previous build artifacts...
if exist build (
    rmdir /s /q build
    echo Removed build\ directory
)
if exist dist (
    rmdir /s /q dist
    echo Removed dist\ directory
)
echo Clean complete!
echo.

REM Step 6: Run PyInstaller
echo [6/8] Building executable with PyInstaller...
echo.
echo =============================================================
echo              PYINSTALLER BUILD OUTPUT
echo =============================================================
echo.

python -m PyInstaller pos_launcher.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Build failed! Check the output above for errors.
    exit /b 1
)

echo.
echo Build completed successfully!
echo.

REM Step 7: Copy config files to dist
echo [7/8] Copying config files to dist...
if exist config.json (
    copy /Y config.json dist\POSLauncher\ >nul
    echo ✓ Copied config.json
) else (
    echo WARNING: config.json not found
)
echo.

REM Step 8: Verify build output
echo [8/8] Verifying build output...
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
