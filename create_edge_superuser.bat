@echo off
REM ========================================
REM Create Superuser for Edge Server
REM ========================================

echo.
echo ========================================
echo   CREATE SUPERUSER - EDGE SERVER
echo ========================================
echo.

set /p USERNAME="Enter username (default: admin): "
if "%USERNAME%"=="" set USERNAME=admin

set /p EMAIL="Enter email (default: admin@edge.local): "
if "%EMAIL%"=="" set EMAIL=admin@edge.local

set /p PASSWORD="Enter password (default: admin123): "
if "%PASSWORD%"=="" set PASSWORD=admin123

echo.
echo Select user role:
echo   1. Admin (access to management dashboard)
echo   2. Manager (access to management dashboard)
echo   3. Cashier (access to POS)
echo   4. Waiter (access to POS)
echo   5. Kitchen (kitchen display only)
echo.
set /p ROLE_CHOICE="Enter choice (default: 1): "
if "%ROLE_CHOICE%"=="" set ROLE_CHOICE=1

if "%ROLE_CHOICE%"=="1" set ROLE=admin
if "%ROLE_CHOICE%"=="2" set ROLE=manager
if "%ROLE_CHOICE%"=="3" set ROLE=cashier
if "%ROLE_CHOICE%"=="4" set ROLE=waiter
if "%ROLE_CHOICE%"=="5" set ROLE=kitchen

echo.
echo Creating superuser with:
echo   Username: %USERNAME%
echo   Email:    %EMAIL%
echo   Password: %PASSWORD%
echo   Role:     %ROLE%
echo.
echo Please wait...
echo.

docker exec fnb_edge_web python manage.py shell -c "from django.contrib.auth import get_user_model; from apps.core.models import Brand; User = get_user_model(); brand = Brand.objects.first(); user = User.objects.create_superuser('%USERNAME%', '%EMAIL%', '%PASSWORD%') if not User.objects.filter(username='%USERNAME%').exists() else User.objects.get(username='%USERNAME%'); user.brand = brand if brand else None; user.role = '%ROLE%'; user.save(); print(f'User created with role: %ROLE%'); print(f'Assigned to brand: {brand.name if brand else \"No brand available\"}')"

echo.
echo ========================================
echo   Superuser created successfully!
echo ========================================
echo.
echo   Username: %USERNAME%
echo   Password: %PASSWORD%
echo   Role:     %ROLE%
echo.
echo   Login at: http://localhost:8001/login/
echo.
if "%ROLE%"=="admin" echo   After login: Redirects to Management Dashboard
if "%ROLE%"=="manager" echo   After login: Redirects to Management Dashboard
if "%ROLE%"=="cashier" echo   After login: Redirects to POS
if "%ROLE%"=="waiter" echo   After login: Redirects to POS
if "%ROLE%"=="kitchen" echo   After login: Redirects to Kitchen Display
echo.

pause
