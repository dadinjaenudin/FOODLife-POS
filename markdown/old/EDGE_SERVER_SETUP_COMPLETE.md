# ✅ Edge Server Docker Setup - COMPLETE

## 🎉 What Has Been Done

### 1. **Docker Compose Configuration**
✅ Created `docker-compose.edge.yml` with no port conflicts:
- PostgreSQL: Port **5433** (HO uses 5432)
- Redis: Port **6380** (HO uses 6379)
- Django Web: Port **8001** (HO uses 8002)

### 2. **Environment Files**
✅ Created environment configuration files:
- `.env.edge` - Docker environment for Edge Server
- `.env.edge.local` - Local development (non-Docker)
- `.env.edge.example` - Template for sharing

### 3. **Helper Scripts (Windows)**
✅ Created batch files for easy management:
- `run_edge_server.bat` - Start Edge Server only
- `stop_edge_server.bat` - Stop Edge Server only
- `start_both_servers.bat` - Start HO + Edge together
- `stop_all_servers.bat` - Stop both servers
- `view_edge_logs.bat` - View Edge Server logs

### 4. **Documentation**
✅ Created comprehensive documentation:
- `README_EDGE_SERVER.md` - Full Edge Server guide
- `PORTS_MAPPING.md` - Detailed port allocation
- `QUICK_START_EDGE_SERVER.md` - Quick setup guide
- `EDGE_SERVER_SETUP_COMPLETE.md` - This file

### 5. **Git Configuration**
✅ Created `.gitignore` to exclude sensitive files:
- Environment files (`.env`, `.env.edge`, etc.)
- Database files
- Logs and temporary files
- Docker volumes

---

## 📊 Port Allocation Summary

| Server | Service | Port | Container Name |
|--------|---------|------|----------------|
| **HO** | Web | 8002 | fnb_ho_web |
| **HO** | PostgreSQL | 5432 | fnb_ho_db |
| **HO** | Redis | 6379 | fnb_ho_redis |
| **Edge** | Web | 8001 | fnb_edge_web |
| **Edge** | PostgreSQL | 5433 | fnb_edge_db |
| **Edge** | Redis | 6380 | fnb_edge_redis |

✅ **No port conflicts - both servers can run simultaneously!**

---

## 🚀 Quick Start Commands

### Start Both Servers
```bash
start_both_servers.bat
```

### Start Individual Server
```bash
# HO Server
docker-compose up -d

# Edge Server
run_edge_server.bat
```

### View Status
```bash
docker ps --filter "name=fnb_"
```

### View Logs
```bash
# Edge logs
view_edge_logs.bat

# HO logs
docker-compose logs -f
```

### Stop Servers
```bash
# Stop both
stop_all_servers.bat

# Stop individual
docker-compose down  # HO
stop_edge_server.bat  # Edge
```

---

## 🔄 Sync Configuration

### Edge Server connects to HO via:
```
HO_API_URL=http://host.docker.internal:8002
```

### From host machine:
```
HO_API_URL=http://localhost:8002
```

---

## 📁 File Structure

```
project/
├── docker-compose.yml              # HO Server (existing)
├── docker-compose.edge.yml         # Edge Server (NEW)
├── .env.docker                     # HO environment (existing)
├── .env.edge                       # Edge environment (NEW)
├── .env.edge.local                 # Edge local env (NEW)
├── .env.edge.example               # Edge template (NEW)
├── .gitignore                      # Git ignore (NEW)
│
├── Helper Scripts (NEW):
│   ├── run_edge_server.bat
│   ├── stop_edge_server.bat
│   ├── start_both_servers.bat
│   ├── stop_all_servers.bat
│   └── view_edge_logs.bat
│
└── Documentation (NEW):
    ├── README_EDGE_SERVER.md
    ├── PORTS_MAPPING.md
    ├── QUICK_START_EDGE_SERVER.md
    └── EDGE_SERVER_SETUP_COMPLETE.md
```

---

## ✅ Pre-Flight Checklist

Before starting development:

- [ ] Docker Desktop is running
- [ ] No services using ports 8001, 5433, 6380
- [ ] `.env.edge` file created (copy from `.env.edge.example`)
- [ ] Both docker-compose files present

---

## 🎯 Next Steps

### 1. **Start Servers**
```bash
start_both_servers.bat
```

### 2. **Setup HO Server** (if not done)
```
http://localhost:8002/setup/
```
- Create Company, Brand, Store
- Run setup_demo

### 3. **Setup Edge Server**
```
http://localhost:8001/setup/
```
- Select existing Company/Brand
- Create new Store for Edge

### 4. **Get HO API Token**
```bash
curl -X POST http://localhost:8002/api/token/ \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
```

### 5. **Configure Edge Sync**
Edit `.env.edge`:
```bash
HO_API_URL=http://host.docker.internal:8002
HO_API_TOKEN=your-actual-jwt-token
```

Restart Edge:
```bash
docker-compose -f docker-compose.edge.yml restart edge_web
```

### 6. **Test Sync**
```bash
# Test from Edge container
docker exec -it fnb_edge_web python manage.py shell
```

```python
import requests
response = requests.get('http://host.docker.internal:8002/api/sync/version/?company_id=YOUR_UUID')
print(response.status_code, response.json())
```

### 7. **Implement Sync Logic**
- Create sync management command
- Test all sync endpoints
- Implement periodic sync with Celery

---

## 📚 Documentation References

| Document | Purpose | When to Read |
|----------|---------|--------------|
| `QUICK_START_EDGE_SERVER.md` | Step-by-step setup | **START HERE** |
| `README_EDGE_SERVER.md` | Complete reference | Detailed info |
| `PORTS_MAPPING.md` | Port allocation | Troubleshooting |
| `SYNC_API_DOCUMENTATION.md` | API reference | Implementing sync |
| `EDGE_SERVER_TESTING_SUMMARY.md` | Testing guide | Testing sync |

---

## 🎉 Success Criteria

After setup, you should have:

✅ HO Server running on port 8002  
✅ Edge Server running on port 8001  
✅ No port conflicts  
✅ Edge can connect to HO  
✅ Both servers have demo data  
✅ Ready to implement sync logic  

---

## 🐛 Common Issues

### Port Already in Use
```bash
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

### Cannot Connect HO from Edge
```bash
# Test connectivity
docker exec -it fnb_edge_web curl http://host.docker.internal:8002/admin/
```

### Container Won't Start
```bash
docker logs fnb_edge_web
docker-compose -f docker-compose.edge.yml restart
```

### Database Migration Error
```bash
docker exec -it fnb_edge_web python manage.py migrate
```

---

## 🎊 READY TO GO!

All Docker configuration is complete and ready for development.

**Next Task:** Implement master data sync from HO to Edge Server.

**Start with:** `QUICK_START_EDGE_SERVER.md`

---

**Setup completed by:** Rovo Dev  
**Date:** 2026-01-27  
**Status:** ✅ Production Ready for Development

---

**Questions?** Check the documentation files above or ask for help!

**Happy Development! 🚀**
