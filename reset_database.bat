@echo off
REM =====================================================
REM  FoodLife POS (Edge) - Reset Database dari Awal
REM  Script ini akan menghapus semua data dan migration,
REM  lalu membuat database baru dari scratch.
REM =====================================================
REM  WARNING: Semua data akan HILANG! Pastikan sudah backup!
REM =====================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ======================================================
echo   FoodLife POS (Edge) - RESET DATABASE DARI AWAL
echo ======================================================
echo.
echo   WARNING: Script ini akan:
echo     1. Stop semua Docker container
echo     2. Hapus Docker volumes (database, minio, dll)
echo     3. Hapus semua migration files
echo     4. Start DB, Redis, MinIO
echo     5. Generate fresh migrations
echo     6. Apply migrations ke database baru
echo     7. Buat admin user + collect static
echo     8. Start semua container
echo.
echo   SEMUA DATA AKAN HILANG!
echo.
echo ======================================================
echo.

set /p CONFIRM="Apakah Anda yakin ingin melanjutkan? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo.
    echo [CANCELLED] Reset database dibatalkan.
    pause
    exit /b 0
)

echo.
set /p BACKUP="Apakah ingin backup database dulu? (y/n): "
if /i "%BACKUP%"=="y" (
    echo.
    echo [STEP 0] Backup database...

    REM Check if container is running
    set DB_CONTAINER=
    for /f "tokens=1" %%A in ('docker ps -q --filter "name=fnb_edge_db" 2^>nul') do set DB_CONTAINER=%%A

    if defined DB_CONTAINER (
        set TIMESTAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
        set TIMESTAMP=!TIMESTAMP: =0!
        set BACKUP_FILE=backup_before_reset_!TIMESTAMP!.sql

        echo [INFO] Membuat backup ke !BACKUP_FILE!...
        docker exec fnb_edge_db pg_dump -U postgres fnb_edge_db > "!BACKUP_FILE!" 2>nul

        if exist "!BACKUP_FILE!" (
            echo [SUCCESS] Backup berhasil: !BACKUP_FILE!
        ) else (
            echo [WARNING] Backup gagal, tapi melanjutkan reset...
        )
    ) else (
        echo [WARNING] Database container tidak running, skip backup...
    )
)

REM ===== STEP 1: Stop containers =====
echo.
echo ======================================================
echo  [STEP 1/8] Stop semua Docker container...
echo ======================================================
docker-compose down 2>nul
if errorlevel 1 (
    docker compose down 2>nul
)
echo [OK] Container stopped.

REM ===== STEP 2: Delete volumes =====
echo.
echo ======================================================
echo  [STEP 2/8] Hapus Docker volumes...
echo ======================================================

REM Volume names dari docker-compose.yml: foodlife-pos_edge_xxx
for %%V in (foodlife-pos_edge_postgres_data foodlife-pos_edge_static_volume foodlife-pos_edge_media_volume foodlife-pos_edge_minio_data) do (
    docker volume rm %%V >nul 2>&1
    if not errorlevel 1 (
        echo [OK] %%V dihapus.
    )
)

REM Juga coba dengan prefix folder name yang mungkin berbeda
for /f "tokens=*" %%V in ('docker volume ls -q --filter "name=edge_postgres_data" 2^>nul') do (
    docker volume rm %%V >nul 2>&1
    echo [OK] %%V dihapus.
)
for /f "tokens=*" %%V in ('docker volume ls -q --filter "name=edge_minio_data" 2^>nul') do (
    docker volume rm %%V >nul 2>&1
    echo [OK] %%V dihapus.
)
for /f "tokens=*" %%V in ('docker volume ls -q --filter "name=edge_static_volume" 2^>nul') do (
    docker volume rm %%V >nul 2>&1
    echo [OK] %%V dihapus.
)
for /f "tokens=*" %%V in ('docker volume ls -q --filter "name=edge_media_volume" 2^>nul') do (
    docker volume rm %%V >nul 2>&1
    echo [OK] %%V dihapus.
)

echo [OK] Docker volumes cleanup selesai.

REM ===== STEP 3: Delete migration files =====
echo.
echo ======================================================
echo  [STEP 3/8] Hapus semua migration files...
echo ======================================================

REM Apps ada di folder apps/ sesuai struktur project
set APPS=core kitchen management pos promotions qr_order tables

for %%A in (%APPS%) do (
    if exist "apps\%%A\migrations" (
        echo [INFO] Cleaning apps\%%A\migrations...
        for %%F in ("apps\%%A\migrations\*.py") do (
            if /i not "%%~nxF"=="__init__.py" (
                del /q "%%F" 2>nul
                echo   - Deleted: %%~nxF
            )
        )
        if exist "apps\%%A\migrations\__pycache__" (
            rmdir /s /q "apps\%%A\migrations\__pycache__" 2>nul
        )
    )
    if exist "apps\%%A\__pycache__" (
        rmdir /s /q "apps\%%A\__pycache__" 2>nul
    )
)

REM Also clean pos_fnb __pycache__
if exist "pos_fnb\__pycache__" (
    rmdir /s /q "pos_fnb\__pycache__" 2>nul
)

echo [OK] Migration files dihapus.

REM ===== STEP 4: Start only DB, Redis, MinIO =====
echo.
echo ======================================================
echo  [STEP 4/8] Start DB, Redis, MinIO (tanpa web/celery)...
echo ======================================================
echo [INFO] Starting edge_db, edge_redis, edge_minio containers...
docker-compose up -d edge_db edge_redis edge_minio 2>nul
if errorlevel 1 (
    docker compose up -d edge_db edge_redis edge_minio 2>nul
)

echo [INFO] Waiting for database to be healthy...
:WAIT_DB
docker exec fnb_edge_db pg_isready -U postgres >nul 2>&1
if errorlevel 1 (
    echo [INFO] Database belum ready, tunggu 3 detik...
    ping -n 4 localhost >nul
    goto WAIT_DB
)
echo [OK] Database ready!

echo [INFO] Waiting for MinIO to be healthy...
ping -n 6 localhost >nul
:WAIT_MINIO
set MINIO_HEALTHY=
for /f "tokens=1" %%A in ('docker ps -q --filter "name=fnb_edge_minio" --filter "health=healthy" 2^>nul') do set MINIO_HEALTHY=%%A
if not defined MINIO_HEALTHY (
    echo [INFO] MinIO belum ready, tunggu 3 detik...
    ping -n 4 localhost >nul
    goto WAIT_MINIO
)
echo [OK] MinIO ready!

REM ===== STEP 5: Generate migrations =====
echo.
echo ======================================================
echo  [STEP 5/8] Generate fresh migrations...
echo ======================================================

echo [INFO] makemigrations core (harus pertama karena app lain depend ke core)...
docker-compose run --rm --no-deps edge_web python manage.py makemigrations core
if errorlevel 1 (
    echo [ERROR] makemigrations core gagal!
    echo [INFO] Pastikan models di apps/core/models.py tidak ada error syntax.
    pause
    exit /b 1
)

echo.
echo [INFO] makemigrations semua app lainnya...
docker-compose run --rm --no-deps edge_web python manage.py makemigrations kitchen management pos promotions qr_order tables
if errorlevel 1 (
    echo [WARNING] Batch makemigrations gagal, mencoba satu per satu...
    for %%A in (kitchen management pos promotions qr_order tables) do (
        echo   - makemigrations %%A...
        docker-compose run --rm --no-deps edge_web python manage.py makemigrations %%A
    )
)

echo.
echo [OK] Fresh migrations generated!

REM ===== STEP 6: Apply migrations =====
echo.
echo ======================================================
echo  [STEP 6/8] Apply migrations ke database baru...
echo ======================================================
echo [INFO] Running migrate...
docker-compose run --rm edge_web python manage.py migrate --noinput
if errorlevel 1 (
    echo [WARNING] Migration gagal, mencoba ulang dalam 5 detik...
    ping -n 6 localhost >nul
    docker-compose run --rm edge_web python manage.py migrate --noinput
    if errorlevel 1 (
        echo [ERROR] Migration tetap gagal!
        pause
        exit /b 1
    )
)
echo [OK] Migrations applied successfully!

REM ===== STEP 7: Create admin + collect static =====
echo.
echo ======================================================
echo  [STEP 7/8] Buat admin user dan setup...
echo ======================================================
echo [INFO] Creating admin superuser...
docker-compose run --rm edge_web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); u, c = User.objects.get_or_create(username='admin', defaults={'email':'admin@edge.local','is_staff':True,'is_superuser':True,'is_active':True,'role':'admin'}); u.set_password('admin123'); u.save(); print('Admin created' if c else 'Admin updated')"
if errorlevel 1 (
    echo [WARNING] Admin creation via shell gagal, mencoba createsuperuser...
    docker-compose run --rm edge_web python manage.py createsuperuser --username admin --email admin@edge.local --noinput 2>nul
)
echo [OK] Admin user created!

echo.
echo [INFO] Collecting static files...
docker-compose run --rm edge_web python manage.py collectstatic --noinput >nul 2>&1
echo [OK] Static files collected!

REM ===== STEP 8: Start all containers =====
echo.
echo ======================================================
echo  [STEP 8/8] Start semua container...
echo ======================================================
echo [INFO] Starting all containers (edge_web, edge_celery_worker, edge_celery_beat)...
docker-compose up -d 2>nul
if errorlevel 1 (
    docker compose up -d 2>nul
)
echo [INFO] Waiting for all containers to start...
ping -n 16 localhost >nul

echo.
echo ======================================================
echo  RESET DATABASE SELESAI!
echo ======================================================
echo.
echo  Database baru telah dibuat dari awal.
echo.
echo  Login credentials:
echo    Username : admin
echo    Password : admin123
echo.
echo  URLs:
echo    POS Web     : http://localhost:8001
echo    MinIO API   : http://localhost:9002
echo    MinIO Console: http://localhost:9003
echo    DB Port     : localhost:5433
echo    Redis Port  : localhost:6380
echo.
echo  Docker containers:
docker-compose ps 2>nul
if errorlevel 1 (
    docker compose ps 2>nul
)
echo.
echo ======================================================
pause
