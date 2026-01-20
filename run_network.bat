@echo off
REM Set development environment variables
set USE_SQLITE=True
set USE_LOCMEM_CACHE=True
set USE_INMEMORY_CHANNEL=True
set DEBUG=True

echo ===============================================
echo Starting Django Server - Network Access Mode
echo ===============================================
echo.
echo Server will be accessible from other computers
echo on the same network.
echo.

REM Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP:~1%

echo Your server will be accessible at:
echo   - Local:   http://127.0.0.1:8000
echo   - Network: http://%IP%:8000
echo.
echo Press Ctrl+C to stop the server
echo ===============================================
echo.

REM Run Django development server on all network interfaces
python manage.py runserver 0.0.0.0:8000
