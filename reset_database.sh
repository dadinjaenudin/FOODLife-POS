#!/bin/bash
# =====================================================
#  FoodLife POS (Edge) - Reset Database dari Awal
#  Script ini akan menghapus semua data dan migration,
#  lalu membuat database baru dari scratch.
# =====================================================
#  WARNING: Semua data akan HILANG! Pastikan sudah backup!
# =====================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Change to script directory
cd "$(dirname "$0")"

# Detect docker compose command (v2 vs v1)
if docker compose version &>/dev/null; then
    DC="docker compose"
elif docker-compose version &>/dev/null; then
    DC="docker-compose"
else
    echo -e "${RED}[ERROR] Docker Compose tidak ditemukan!${NC}"
    exit 1
fi

echo ""
echo -e "${BOLD}${CYAN}======================================================"
echo "  FoodLife POS (Edge) - RESET DATABASE DARI AWAL"
echo "======================================================${NC}"
echo ""
echo -e "  ${YELLOW}WARNING: Script ini akan:${NC}"
echo "    1. Stop semua Docker container"
echo "    2. Hapus Docker volumes (database, minio, dll)"
echo "    3. Hapus semua migration files"
echo "    4. Start DB, Redis, MinIO"
echo "    5. Generate fresh migrations"
echo "    6. Apply migrations ke database baru"
echo "    7. Buat admin user + collect static"
echo "    8. Start semua container"
echo ""
echo -e "  ${RED}${BOLD}SEMUA DATA AKAN HILANG!${NC}"
echo ""
echo -e "${CYAN}======================================================${NC}"
echo ""

read -p "Apakah Anda yakin ingin melanjutkan? (y/n): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}[CANCELLED] Reset database dibatalkan.${NC}"
    exit 0
fi

echo ""
read -p "Apakah ingin backup database dulu? (y/n): " BACKUP
if [[ "$BACKUP" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}[STEP 0] Backup database...${NC}"

    # Check if container is running
    DB_CONTAINER=$(docker ps -q --filter "name=fnb_edge_db" 2>/dev/null)

    if [ -n "$DB_CONTAINER" ]; then
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_FILE="backup_before_reset_${TIMESTAMP}.sql"

        echo -e "[INFO] Membuat backup ke ${BACKUP_FILE}..."
        if docker exec fnb_edge_db pg_dump -U postgres fnb_edge_db > "$BACKUP_FILE" 2>/dev/null; then
            BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            echo -e "${GREEN}[SUCCESS] Backup berhasil: ${BACKUP_FILE} (${BACKUP_SIZE})${NC}"
        else
            echo -e "${YELLOW}[WARNING] Backup gagal, tapi melanjutkan reset...${NC}"
        fi
    else
        echo -e "${YELLOW}[WARNING] Database container tidak running, skip backup...${NC}"
    fi
fi

# ===== STEP 1: Stop containers =====
echo ""
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo -e "${BOLD} [STEP 1/8] Stop semua Docker container...${NC}"
echo -e "${BOLD}${CYAN}======================================================${NC}"
$DC down 2>/dev/null || true
echo -e "${GREEN}[OK] Container stopped.${NC}"

# ===== STEP 2: Delete volumes =====
echo ""
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo -e "${BOLD} [STEP 2/8] Hapus Docker volumes...${NC}"
echo -e "${BOLD}${CYAN}======================================================${NC}"

# Find and remove all edge volumes (handles different project name prefixes)
for FILTER in "edge_postgres_data" "edge_minio_data" "edge_static_volume" "edge_media_volume"; do
    VOLS=$(docker volume ls -q --filter "name=${FILTER}" 2>/dev/null)
    for V in $VOLS; do
        if docker volume rm "$V" &>/dev/null; then
            echo -e "${GREEN}[OK] ${V} dihapus.${NC}"
        fi
    done
done

# Also try exact names
for V in foodlife-pos_edge_postgres_data foodlife-pos_edge_static_volume foodlife-pos_edge_media_volume foodlife-pos_edge_minio_data; do
    docker volume rm "$V" &>/dev/null && echo -e "${GREEN}[OK] ${V} dihapus.${NC}" || true
done

echo -e "${GREEN}[OK] Docker volumes cleanup selesai.${NC}"

# ===== STEP 3: Delete migration files =====
echo ""
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo -e "${BOLD} [STEP 3/8] Hapus semua migration files...${NC}"
echo -e "${BOLD}${CYAN}======================================================${NC}"

APPS="core kitchen management pos promotions qr_order tables"

for APP in $APPS; do
    MIG_DIR="apps/${APP}/migrations"
    if [ -d "$MIG_DIR" ]; then
        echo "[INFO] Cleaning ${MIG_DIR}..."
        COUNT=0
        for F in "$MIG_DIR"/[0-9]*.py; do
            [ -f "$F" ] || continue
            rm -f "$F"
            echo "  - Deleted: $(basename "$F")"
            COUNT=$((COUNT + 1))
        done
        [ $COUNT -eq 0 ] && echo "  - No migration files found"

        # Clean __pycache__
        rm -rf "$MIG_DIR/__pycache__" 2>/dev/null
    fi
    rm -rf "apps/${APP}/__pycache__" 2>/dev/null
done

# Also clean pos_fnb __pycache__
rm -rf "pos_fnb/__pycache__" 2>/dev/null

echo -e "${GREEN}[OK] Migration files dihapus.${NC}"

# ===== STEP 4: Start only DB, Redis, MinIO =====
echo ""
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo -e "${BOLD} [STEP 4/8] Start DB, Redis, MinIO (tanpa web/celery)...${NC}"
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo "[INFO] Starting edge_db, edge_redis, edge_minio containers..."
$DC up -d edge_db edge_redis edge_minio

echo "[INFO] Waiting for database to be healthy..."
RETRIES=0
MAX_RETRIES=30
while ! docker exec fnb_edge_db pg_isready -U postgres &>/dev/null; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -ge $MAX_RETRIES ]; then
        echo -e "${RED}[ERROR] Database tidak ready setelah ${MAX_RETRIES} percobaan!${NC}"
        exit 1
    fi
    echo "[INFO] Database belum ready, tunggu 3 detik... (${RETRIES}/${MAX_RETRIES})"
    sleep 3
done
echo -e "${GREEN}[OK] Database ready!${NC}"

echo "[INFO] Waiting for MinIO to be healthy..."
sleep 5
RETRIES=0
while [ -z "$(docker ps -q --filter 'name=fnb_edge_minio' --filter 'health=healthy' 2>/dev/null)" ]; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -ge $MAX_RETRIES ]; then
        echo -e "${RED}[ERROR] MinIO tidak ready setelah ${MAX_RETRIES} percobaan!${NC}"
        exit 1
    fi
    echo "[INFO] MinIO belum ready, tunggu 3 detik... (${RETRIES}/${MAX_RETRIES})"
    sleep 3
done
echo -e "${GREEN}[OK] MinIO ready!${NC}"

# ===== STEP 5: Generate migrations =====
echo ""
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo -e "${BOLD} [STEP 5/8] Generate fresh migrations...${NC}"
echo -e "${BOLD}${CYAN}======================================================${NC}"

echo "[INFO] makemigrations core (harus pertama karena app lain depend ke core)..."
if ! $DC run --rm --no-deps edge_web python manage.py makemigrations core; then
    echo -e "${RED}[ERROR] makemigrations core gagal!${NC}"
    echo "[INFO] Pastikan models di apps/core/models.py tidak ada error syntax."
    exit 1
fi

echo ""
echo "[INFO] makemigrations semua app lainnya..."
if ! $DC run --rm --no-deps edge_web python manage.py makemigrations kitchen management pos promotions qr_order tables; then
    echo -e "${YELLOW}[WARNING] Batch makemigrations gagal, mencoba satu per satu...${NC}"
    for APP in kitchen management pos promotions qr_order tables; do
        echo "  - makemigrations ${APP}..."
        $DC run --rm --no-deps edge_web python manage.py makemigrations "$APP" || true
    done
fi

echo ""
echo -e "${GREEN}[OK] Fresh migrations generated!${NC}"

# ===== STEP 6: Apply migrations =====
echo ""
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo -e "${BOLD} [STEP 6/8] Apply migrations ke database baru...${NC}"
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo "[INFO] Running migrate..."
if ! $DC run --rm edge_web python manage.py migrate --noinput; then
    echo -e "${YELLOW}[WARNING] Migration gagal, mencoba ulang dalam 5 detik...${NC}"
    sleep 5
    if ! $DC run --rm edge_web python manage.py migrate --noinput; then
        echo -e "${RED}[ERROR] Migration tetap gagal!${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}[OK] Migrations applied successfully!${NC}"

# ===== STEP 7: Create admin + collect static =====
echo ""
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo -e "${BOLD} [STEP 7/8] Buat admin user dan setup...${NC}"
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo "[INFO] Creating admin superuser..."
$DC run --rm edge_web python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u, c = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@edge.local',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
        'role': 'admin'
    }
)
u.set_password('admin123')
u.save()
print('Admin created' if c else 'Admin updated')
" || {
    echo -e "${YELLOW}[WARNING] Admin creation via shell gagal, mencoba createsuperuser...${NC}"
    $DC run --rm edge_web python manage.py createsuperuser --username admin --email admin@edge.local --noinput 2>/dev/null || true
}
echo -e "${GREEN}[OK] Admin user created!${NC}"

echo ""
echo "[INFO] Collecting static files..."
$DC run --rm edge_web python manage.py collectstatic --noinput &>/dev/null
echo -e "${GREEN}[OK] Static files collected!${NC}"

# ===== STEP 8: Start all containers =====
echo ""
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo -e "${BOLD} [STEP 8/8] Start semua container...${NC}"
echo -e "${BOLD}${CYAN}======================================================${NC}"
echo "[INFO] Starting all containers (edge_web, edge_celery_worker, edge_celery_beat)..."
$DC up -d
echo "[INFO] Waiting for all containers to start..."
sleep 15

echo ""
echo -e "${BOLD}${GREEN}======================================================${NC}"
echo -e "${BOLD}${GREEN} RESET DATABASE SELESAI!${NC}"
echo -e "${BOLD}${GREEN}======================================================${NC}"
echo ""
echo -e "  Database baru telah dibuat dari awal."
echo ""
echo -e "  ${BOLD}Login credentials:${NC}"
echo -e "    Username : ${CYAN}admin${NC}"
echo -e "    Password : ${CYAN}admin123${NC}"
echo ""
echo -e "  ${BOLD}URLs:${NC}"
echo -e "    POS Web      : ${CYAN}http://localhost:8001${NC}"
echo -e "    MinIO API    : ${CYAN}http://localhost:9002${NC}"
echo -e "    MinIO Console : ${CYAN}http://localhost:9003${NC}"
echo -e "    DB Port      : ${CYAN}localhost:5433${NC}"
echo -e "    Redis Port   : ${CYAN}localhost:6380${NC}"
echo ""
echo -e "  ${BOLD}Docker containers:${NC}"
$DC ps
echo ""
echo -e "${BOLD}${GREEN}======================================================${NC}"
