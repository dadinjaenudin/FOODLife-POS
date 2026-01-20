@echo off
REM ====================================================================
REM Seed Sample Transaction Data
REM ====================================================================
echo.
echo ========================================
echo SEED TRANSACTION DATA
echo ========================================
echo.

REM Set environment to use SQLite
set USE_SQLITE=True

set /p COUNT="How many bills to create? (default 10): "
if "%COUNT%"=="" set COUNT=10

echo.
echo Creating %COUNT% sample bills...
echo.

python manage.py seed_transactions --count %COUNT%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS: %COUNT% bills created!
    echo ========================================
    echo.
    echo Open KDS to view:
    echo   Kitchen: http://127.0.0.1:8000/kitchen/kds/kitchen/
    echo   Bar:     http://127.0.0.1:8000/kitchen/kds/bar/
) else (
    echo.
    echo ========================================
    echo ERROR: Failed to seed data
    echo ========================================
    pause
    exit /b 1
)

echo.
pause
