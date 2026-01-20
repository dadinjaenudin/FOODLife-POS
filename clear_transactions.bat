@echo off
REM ====================================================================
REM Clear All Transaction Data
REM ====================================================================
echo.
echo ========================================
echo CLEAR TRANSACTION DATA
echo ========================================
echo.
echo This will DELETE all:
echo - Bills
echo - Bill Items  
echo - Payments
echo - Kitchen Orders
echo - Bill Logs
echo - Reset table status
echo.
pause

REM Set environment to use SQLite
set USE_SQLITE=True

python manage.py clear_transactions --yes

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS: All transaction data cleared!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ERROR: Failed to clear data
    echo ========================================
    pause
    exit /b 1
)

echo.
pause
