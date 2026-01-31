# 🚀 START HERE - Edge Server Setup

## ✅ Docker Configuration Complete!

All files have been created and configured with **NO PORT CONFLICTS**.

---

## 📊 Quick Reference

### Ports (No Conflicts!)
| Server | Web | PostgreSQL | Redis |
|--------|-----|------------|-------|
| **HO** | 8002 | 5432 | 6379 |
| **Edge** | 8001 | 5433 | 6380 |

### Access URLs
- **HO Server**: http://localhost:8002
- **Edge Server**: http://localhost:8001

---

## 🎯 Step-by-Step Setup (5 Minutes)

### Step 1: Start Both Servers
```bash
# Double-click this file:
start_both_servers.bat

# Wait 10-15 seconds...
```

### Step 2: Verify Containers Running
```bash
docker ps --filter "name=fnb_"
```

You should see:
- ✅ fnb_ho_web (port 8002)
- ✅ fnb_ho_db (port 5432)
- ✅ fnb_ho_redis (port 6379)
- ✅ fnb_edge_web (port 8001)
- ✅ fnb_edge_db (port 5433)
- ✅ fnb_edge_redis (port 6380)

### Step 3: Setup HO Server (if not done)
1. Open: http://localhost:8002/setup/
2. Create Company, Brand, Store
3. Run demo data:
   ```bash
   docker exec -it fnb_ho_web python manage.py setup_demo
   ```

### Step 4: Setup Edge Server
1. Open: http://localhost:8001/setup/
2. Select existing Company/Brand
3. Create NEW Store (e.g., "Cabang BSD")
4. Complete setup ✅

### Step 5: Configure Sync
1. Get token from HO:
   ```bash
   curl -X POST http://localhost:8002/api/token/ \
     -H "Content-Type: application/json" \
     -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
   ```

2. Copy the `access` token

3. Edit `.env.edge`:
   ```
   HO_API_TOKEN=your-actual-token-here
   ```

4. Restart Edge:
   ```bash
   docker-compose -f docker-compose.edge.yml restart edge_web
   ```

---

## 🎉 You're Ready!

### Test Sync Connection
```bash
docker exec -it fnb_edge_web python manage.py shell
```

```python
import requests
response = requests.get('http://host.docker.internal:8002/api/sync/version/?company_id=YOUR_UUID')
print(response.status_code)  # Should be 200
```

---

## 📚 Documentation

| File | When to Read |
|------|-------------|
| **QUICK_START_EDGE_SERVER.md** | 👈 Read this first! |
| README_EDGE_SERVER.md | Detailed reference |
| PORTS_MAPPING.md | Port troubleshooting |
| SYNC_API_DOCUMENTATION.md | Implementing sync |

---

## 🛑 Stop Servers

```bash
# Double-click:
stop_all_servers.bat
```

---

## 🐛 Troubleshooting

### Port already in use?
```bash
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

### Container won't start?
```bash
docker logs fnb_edge_web
```

### Can't connect to HO?
```bash
docker exec -it fnb_edge_web curl http://host.docker.internal:8002/admin/
```

---

## 🎯 Current Status

✅ **Docker Setup**: Complete  
✅ **Port Configuration**: No conflicts  
✅ **Environment Files**: Ready  
✅ **Helper Scripts**: Created  
✅ **Documentation**: Complete  

**Next Task**: Start servers and test sync! 🚀

---

**Quick Start Command:**
```bash
start_both_servers.bat
```

**Then Read:**
- `QUICK_START_EDGE_SERVER.md`

---

**All set! Let's sync master data! 🎉**
