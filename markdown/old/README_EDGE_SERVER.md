# Edge Server - Development Setup

## 🎯 Overview

Ini adalah setup untuk **Edge Server** yang berjalan bersamaan dengan **HO Server** di satu PC untuk development.

---

## 📊 Port Mapping

### HO Server (Head Office)
| Service | Internal Port | External Port | URL |
|---------|--------------|---------------|-----|
| PostgreSQL | 5432 | **5432** | localhost:5432 |
| Redis | 6379 | **6379** | localhost:6379 |
| Django Web | 8000 | **8002** | http://localhost:8002 |

### Edge Server (Store)
| Service | Internal Port | External Port | URL |
|---------|--------------|---------------|-----|
| PostgreSQL | 5432 | **5433** | localhost:5433 |
| Redis | 6379 | **6380** | localhost:6380 |
| Django Web | 8000 | **8001** | http://localhost:8001 |

---

## 🚀 Quick Start

### 1. Start HO Server (if not running)
```bash
docker-compose up -d
```
**Access:** http://localhost:8002

### 2. Start Edge Server
```bash
docker-compose -f docker-compose.edge.yml up -d
```
**Access:** http://localhost:8001

### 3. Check Running Containers
```bash
docker ps
```

Should show:
```
CONTAINER ID   IMAGE                  PORTS                    NAMES
...            postgres:16-alpine    0.0.0.0:5432->5432/tcp   fnb_ho_db
...            postgres:16-alpine    0.0.0.0:5433->5432/tcp   fnb_edge_db
...            redis:7-alpine        0.0.0.0:6379->6379/tcp   fnb_ho_redis
...            redis:7-alpine        0.0.0.0:6380->6379/tcp   fnb_edge_redis
...            app                   0.0.0.0:8002->8000/tcp   fnb_ho_web
...            app                   0.0.0.0:8001->8000/tcp   fnb_edge_web
```

---

## 🔧 Setup Edge Server

### 1. Run Migrations
```bash
docker exec -it fnb_edge_web python manage.py migrate
```

### 2. Create Superuser
```bash
docker exec -it fnb_edge_web python manage.py createsuperuser
```

### 3. Run Setup Demo (Optional)
```bash
docker exec -it fnb_edge_web python manage.py setup_demo
```

### 4. Access Edge Server Setup Wizard
```
http://localhost:8001/setup/
```

**Setup Steps:**
1. Create Company (or use existing)
2. Create Brand/Outlet
3. Create Store for this Edge Server
4. Complete setup

---

## 🔄 Sync Configuration

### Get HO API Token

**Option 1: Using Django Admin**
1. Login to HO Server: http://localhost:8002/admin
2. Go to: Authentication and Authorization → Tokens
3. Create token for sync user
4. Copy the token

**Option 2: Using API**
```bash
curl -X POST http://localhost:8002/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Copy the `access` token.

### Update Edge Server .env

Edit `.env.edge`:
```bash
HO_API_URL=http://host.docker.internal:8002
HO_API_TOKEN=your-actual-token-here
```

Restart Edge Server:
```bash
docker-compose -f docker-compose.edge.yml restart edge_web
```

---

## 📥 Test Sync

### 1. Check HO Server Sync Dashboard
```
http://localhost:8002/promotions/compiler/
```

### 2. Test Version Check from Edge
```bash
docker exec -it fnb_edge_web python manage.py shell
```

```python
import requests

# Test connection to HO
response = requests.get('http://host.docker.internal:8002/api/sync/version/?company_id=YOUR_COMPANY_UUID')
print(response.status_code)
print(response.json())
```

### 3. Run Manual Sync (if sync command exists)
```bash
docker exec -it fnb_edge_web python manage.py sync_from_ho --type all
```

---

## 🛠️ Development Workflow

### Run Edge Server Locally (Outside Docker)

If you want to run Edge Server outside Docker (for easier debugging):

1. **Stop Docker Edge Web** (keep DB & Redis running):
```bash
docker stop fnb_edge_web fnb_edge_celery_worker fnb_edge_celery_beat
```

2. **Use local environment**:
```bash
# Copy local env
cp .env.edge.local .env

# Run migrations
python manage.py migrate

# Run server
python manage.py runserver 8001
```

3. **Run Celery (if needed)**:
```bash
# Terminal 1: Worker
celery -A pos_fnb worker -l info

# Terminal 2: Beat
celery -A pos_fnb beat -l info
```

---

## 📝 Useful Commands

### View Logs
```bash
# All Edge Server logs
docker-compose -f docker-compose.edge.yml logs -f

# Specific service
docker-compose -f docker-compose.edge.yml logs -f edge_web
docker-compose -f docker-compose.edge.yml logs -f edge_db
docker-compose -f docker-compose.edge.yml logs -f edge_celery_worker
```

### Database Access
```bash
# PostgreSQL Edge
docker exec -it fnb_edge_db psql -U postgres -d fnb_edge_db

# Redis Edge
docker exec -it fnb_edge_redis redis-cli
```

### Restart Services
```bash
# Restart all Edge services
docker-compose -f docker-compose.edge.yml restart

# Restart specific service
docker-compose -f docker-compose.edge.yml restart edge_web
```

### Stop Services
```bash
# Stop Edge Server
docker-compose -f docker-compose.edge.yml down

# Stop Edge Server and remove volumes (DANGER: deletes data)
docker-compose -f docker-compose.edge.yml down -v
```

---

## 🔍 Troubleshooting

### Port Already in Use
```bash
# Check what's using the port
netstat -ano | findstr :5433
netstat -ano | findstr :6380
netstat -ano | findstr :8001

# Kill the process if needed
taskkill /PID <PID> /F
```

### Cannot Connect to HO Server
From inside Edge container, HO Server is accessible via:
- `http://host.docker.internal:8002` (recommended)
- `http://172.17.0.1:8002` (Docker default gateway)

Test connection:
```bash
docker exec -it fnb_edge_web curl http://host.docker.internal:8002/api/sync/version/
```

### Database Connection Failed
Check if PostgreSQL is running:
```bash
docker ps | grep fnb_edge_db
docker logs fnb_edge_db
```

### Redis Connection Failed
Check if Redis is running:
```bash
docker ps | grep fnb_edge_redis
docker logs fnb_edge_redis
```

---

## 🎯 Testing Sync Flow

### 1. Prepare HO Server
```bash
# Ensure HO has sample data
docker exec -it fnb_ho_web python manage.py setup_demo

# Check HO Dashboard
# http://localhost:8002/promotions/compiler/
```

### 2. Setup Edge Server
```bash
# Access setup wizard
# http://localhost:8001/setup/

# Or use command
docker exec -it fnb_edge_web python manage.py setup_store
```

### 3. Get Sync Credentials
```bash
# Get token from HO
curl -X POST http://localhost:8002/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 4. Update Edge Config
Edit `.env.edge` and restart:
```bash
docker-compose -f docker-compose.edge.yml restart
```

### 5. Test Sync Endpoints
```bash
# From host machine
export TOKEN="your-jwt-token"
export COMPANY_ID="your-company-uuid"
export STORE_ID="your-store-uuid"

# Test version
curl "http://localhost:8002/api/sync/version/?company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN"

# Test promotions
curl "http://localhost:8002/api/sync/promotions/?store_id=$STORE_ID&company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN"

# Test products
curl "http://localhost:8002/api/sync/products/?company_id=$COMPANY_ID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🎉 Summary

✅ **HO Server**: Port 8002, DB 5432, Redis 6379  
✅ **Edge Server**: Port 8001, DB 5433, Redis 6380  
✅ **No Port Conflicts**: Both can run simultaneously  
✅ **Sync Ready**: Edge can connect to HO via `host.docker.internal:8002`  

**Next Steps:**
1. Start both servers
2. Setup Edge Server via wizard
3. Configure sync credentials
4. Test sync endpoints
5. Implement sync logic

---

**Happy Development! 🚀**
