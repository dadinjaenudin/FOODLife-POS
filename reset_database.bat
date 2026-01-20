@echo off
REM ====================================================================
REM Reset Database - Clear and Seed Fresh Data
REM ====================================================================
echo.
echo ========================================
echo RESET DATABASE
echo ========================================
echo.
echo This will:
echo 1. Clear all transaction data
echo 2. Seed 20 fresh sample bills
echo.
pause

REM Set environment to use SQLite
set USE_SQLITE=True

REM Clear existing data
echo.
echo [1/2] Clearing existing data...
python manage.py clear_transactions --yes

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to clear data
    pause
    exit /b 1
)

REM Seed fresh data
echo.
echo [2/2] Seeding fresh data...
python manage.py seed_transactions --count 20

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to seed data
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS: Database reset complete!
echo ========================================
echo.
echo 20 fresh bills created with:
echo - Dine-in orders (open)
echo - Dine-in orders (paid)
echo - Take away orders
echo - Hold orders
echo.
echo Open KDS to view:
echo   Kitchen: http://127.0.0.1:8000/kitchen/kds/kitchen/
echo   Bar:     http://127.0.0.1:8000/kitchen/kds/bar/
echo   POS:     http://127.0.0.1:8000/
echo.
pause
