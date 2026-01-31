# 🔌 Port Mapping - Development Environment

## Overview

Untuk development di satu PC, kita menjalankan **HO Server** dan **Edge Server** secara bersamaan dengan port yang berbeda.

---

## 📊 Port Allocation

### **HO Server (Head Office)**

| Service | Container Name | Internal Port | External Port | Access URL |
|---------|---------------|---------------|---------------|------------|
| **Django Web** | `fnb_ho_web` | 8000 | **8002** | http://localhost:8002 |
| **PostgreSQL** | `fnb_ho_db` | 5432 | **5432** | localhost:5432 |
| **Redis** | `fnb_ho_redis` | 6379 | **6379** | localhost:6379 |
| **Celery Worker** | `fnb_ho_celery_worker` | - | - | - |
| **Celery Beat** | `fnb_ho_celery_beat` | - | - | - |

**Docker Compose File:** `docker-compose.yml`

---

### **Edge Server (Store/POS)**

| Service | Container Name | Internal Port | External Port | Access URL |
|---------|---------------|---------------|---------------|------------|
| **Django Web** | `fnb_edge_web` | 8000 | **8001** | http://localhost:8001 |
| **PostgreSQL** | `fnb_edge_db` | 5432 | **5433** | localhost:5433 |
| **Redis** | `fnb_edge_redis` | 6379 | **6380** | localhost:6380 |
| **Celery Worker** | `fnb_edge_celery_worker` | - | - | - |
| **Celery Beat** | `fnb_edge_celery_beat` | - | - | - |

**Docker Compose File:** `docker-compose.edge.yml`

---

## 🎯 Quick Access URLs

### HO Server
- **Main Application**: http://localhost:8002
- **Admin Panel**: http://localhost:8002/admin/
- **Promotion Compiler**: http://localhost:8002/promotions/compiler/
- **API Token**: http://localhost:8002/api/token/
- **Sync API Base**: http://localhost:8002/api/sync/

### Edge Server
- **Main Application**: http://localhost:8001
- **Admin Panel**: http://localhost:8001/admin/
- **Setup Wizard**: http://localhost:8001/setup/
- **Terminal Setup**: http://localhost:8001/setup/terminal/
- **POS Interface**: http://localhost:8001/

---

## 🔄 Inter-Server Communication

### Edge Server → HO Server

**From Host Machine:**
```bash
curl http://localhost:8002/api/sync/version/
```

**From Inside Edge Container:**
```bash
# Use host.docker.internal to access host machine
curl http://host.docker.internal:8002/api/sync/version/
```

**Configuration in .env.edge:**
```bash
HO_API_URL=http://host.docker.internal:8002
```

---

## 🛠️ Database Connections

### HO Database (PostgreSQL)
```bash
# From host machine
psql -h localhost -p 5432 -U postgres -d fnb_ho_db

# From Docker
docker exec -it fnb_ho_db psql -U postgres -d fnb_ho_db

# Connection String
postgresql://postgres:postgres123@localhost:5432/fnb_ho_db
```

### Edge Database (PostgreSQL)
```bash
# From host machine
psql -h localhost -p 5433 -U postgres -d fnb_edge_db

# From Docker
docker exec -it fnb_edge_db psql -U postgres -d fnb_edge_db

# Connection String
postgresql://postgres:postgres123@localhost:5433/fnb_edge_db
```

---

## 🔴 Redis Connections

### HO Redis
```bash
# From host machine
redis-cli -h localhost -p 6379

# From Docker
docker exec -it fnb_ho_redis redis-cli

# Connection String
redis://localhost:6379/0
```

### Edge Redis
```bash
# From host machine
redis-cli -h localhost -p 6380

# From Docker
docker exec -it fnb_edge_redis redis-cli

# Connection String
redis://localhost:6380/0
```

---

## 🚀 Start/Stop Commands

### Start Both Servers
```bash
# Windows
start_both_servers.bat

# Linux/Mac
docker-compose up -d
docker-compose -f docker-compose.edge.yml up -d
```

### Start Individual Server
```bash
# HO Server only
docker-compose up -d

# Edge Server only
run_edge_server.bat
# or
docker-compose -f docker-compose.edge.yml up -d
```

### Stop Servers
```bash
# Stop all
stop_all_servers.bat

# Stop HO only
docker-compose down

# Stop Edge only
stop_edge_server.bat
# or
docker-compose -f docker-compose.edge.yml down
```

---

## 🔍 Troubleshooting

### Check Running Containers
```bash
docker ps --filter "name=fnb_"
```

**Expected Output:**
```
CONTAINER ID   IMAGE                  PORTS                    NAMES
xxxxx          postgres:16-alpine    0.0.0.0:5432->5432/tcp   fnb_ho_db
xxxxx          postgres:16-alpine    0.0.0.0:5433->5432/tcp   fnb_edge_db
xxxxx          redis:7-alpine        0.0.0.0:6379->6379/tcp   fnb_ho_redis
xxxxx          redis:7-alpine        0.0.0.0:6380->6379/tcp   fnb_edge_redis
xxxxx          app                   0.0.0.0:8002->8000/tcp   fnb_ho_web
xxxxx          app                   0.0.0.0:8001->8000/tcp   fnb_edge_web
```

### Port Already in Use
```bash
# Windows - Check what's using the port
netstat -ano | findstr :8001
netstat -ano | findstr :8002
netstat -ano | findstr :5432
netstat -ano | findstr :5433
netstat -ano | findstr :6379
netstat -ano | findstr :6380

# Kill process if needed
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8001
lsof -i :8002
kill -9 <PID>
```

### Container Won't Start
```bash
# View logs
docker logs fnb_edge_web
docker logs fnb_ho_web

# View all Edge logs
view_edge_logs.bat
# or
docker-compose -f docker-compose.edge.yml logs -f
```

### Cannot Connect Between Servers
```bash
# Test from Edge container to HO
docker exec -it fnb_edge_web curl http://host.docker.internal:8002/admin/

# If fails, try Docker gateway IP
docker exec -it fnb_edge_web curl http://172.17.0.1:8002/admin/
```

---

## 📝 Environment Files

### HO Server
- **Docker**: `.env.docker`
- **Local**: `.env`

### Edge Server
- **Docker**: `.env.edge`
- **Local**: `.env.edge.local`

---

## ✅ Pre-Flight Checklist

Before starting development:

- [ ] Docker Desktop is running
- [ ] Port 8001 is free (Edge Web)
- [ ] Port 8002 is free (HO Web)
- [ ] Port 5432 is free (HO DB)
- [ ] Port 5433 is free (Edge DB)
- [ ] Port 6379 is free (HO Redis)
- [ ] Port 6380 is free (Edge Redis)
- [ ] `.env.edge` file exists and configured
- [ ] `.env.docker` file exists and configured

---

## 🎉 Summary

| Server | Web UI | Database | Redis | Docker Compose |
|--------|--------|----------|-------|----------------|
| **HO** | :8002 | :5432 | :6379 | `docker-compose.yml` |
| **Edge** | :8001 | :5433 | :6380 | `docker-compose.edge.yml` |

✅ **No port conflicts**  
✅ **Both servers can run simultaneously**  
✅ **Edge can sync from HO via `host.docker.internal:8002`**  

---

**Ready for development! 🚀**
