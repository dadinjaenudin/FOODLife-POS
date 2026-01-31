# ⚡ Quick Start - Edge Server Development

## 🎯 Goal
Run **HO Server** (port 8002) and **Edge Server** (port 8001) simultaneously on one PC.

---

## 🚀 Step-by-Step Setup

### **Step 1: Start Both Servers**
```bash
# Double-click this file:
start_both_servers.bat

# Or manually:
docker-compose up -d
docker-compose -f docker-compose.edge.yml up -d
```

**Wait 10-15 seconds for services to start.**

---

### **Step 2: Verify Both Servers Running**
```bash
docker ps --filter "name=fnb_"
```

Should show 10+ containers running:
- `fnb_ho_web`, `fnb_ho_db`, `fnb_ho_redis`
- `fnb_edge_web`, `fnb_edge_db`, `fnb_edge_redis`

---

### **Step 3: Setup HO Server (if not done)**

**3.1. Access HO:**
```
http://localhost:8002/setup/
```

**3.2. Create:**
- Company: `YOGYA DEPARTMENT STORE` (Code: `YOGYA`)
- Brand: `Ayam Geprek Express` (Code: `YOGYA-001`)
- Store: `HO Pusat` (Code: `YOGYA001-HQ`)

**3.3. Create Demo Data:**
```bash
docker exec -it fnb_ho_web python manage.py setup_demo
```

**3.4. Login HO Admin:**
```
http://localhost:8002/admin/
Username: admin
Password: admin123
```

---

### **Step 4: Setup Edge Server**

**4.1. Access Edge:**
```
http://localhost:8001/setup/
```

**4.2. Create Store:**
- Use existing Company: `YOGYA DEPARTMENT STORE`
- Use existing Brand: `Ayam Geprek Express`
- Create NEW Store: `Cabang BSD` (Code: `YOGYA001-BSD`)

**4.3. Complete Setup**

You should see: ✅ **Edge Server Configured!**

---

### **Step 5: Get HO API Token**

**5.1. Get JWT Token:**
```bash
curl -X POST http://localhost:8002/api/token/ \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
```

**5.2. Copy the `access` token** (looks like: `eyJ0eXAiOiJKV1QiLCJh...`)

**5.3. Test Token:**
```bash
# Replace YOUR_COMPANY_UUID with actual UUID from HO
curl "http://localhost:8002/api/sync/version/?company_id=YOUR_COMPANY_UUID" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

If successful, you'll see: `{"version": 1, "updated_at": "..."}`

---

### **Step 6: Configure Edge Server Sync**

**6.1. Edit `.env.edge`:**
```bash
HO_API_URL=http://host.docker.internal:8002
HO_API_TOKEN=YOUR_ACTUAL_JWT_TOKEN_HERE
```

**6.2. Restart Edge Server:**
```bash
docker-compose -f docker-compose.edge.yml restart edge_web
```

---

### **Step 7: Test Sync from Edge**

**7.1. Open Edge Django Shell:**
```bash
docker exec -it fnb_edge_web python manage.py shell
```

**7.2. Test Connection:**
```python
import requests
import os

# Get config
ho_url = os.getenv('HO_API_URL', 'http://host.docker.internal:8002')
ho_token = os.getenv('HO_API_TOKEN')

print(f"HO URL: {ho_url}")
print(f"Token: {ho_token[:20]}..." if ho_token else "Token: NOT SET")

# Test version endpoint
headers = {'Authorization': f'Bearer {ho_token}'}
response = requests.get(f'{ho_url}/api/sync/version/?company_id=YOUR_UUID', headers=headers)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

Expected output:
```json
{
  "version": 1,
  "updated_at": "2026-01-27T10:00:00Z"
}
```

---

## 🎉 Success Checklist

- [ ] HO Server running on http://localhost:8002
- [ ] Edge Server running on http://localhost:8001
- [ ] HO has demo data (products, categories)
- [ ] Edge Server configured with store
- [ ] JWT token obtained from HO
- [ ] Edge can connect to HO (test successful)

---

## 🔧 Common Issues & Solutions

### ❌ Port 8001 already in use
```bash
# Windows
netstat -ano | findstr :8001
taskkill /PID <PID> /F

# Then restart
docker-compose -f docker-compose.edge.yml restart
```

### ❌ Cannot connect to HO from Edge
```bash
# Test from inside Edge container
docker exec -it fnb_edge_web curl http://host.docker.internal:8002/admin/

# If fails, check HO is running
curl http://localhost:8002/admin/
```

### ❌ 401 Unauthorized error
```bash
# Token expired - get new token
curl -X POST http://localhost:8002/api/token/ \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"admin123\"}"

# Update .env.edge with new token
# Restart Edge
docker-compose -f docker-compose.edge.yml restart edge_web
```

### ❌ Database migration error
```bash
# Run migrations manually
docker exec -it fnb_edge_web python manage.py migrate
```

---

## 📱 Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| **HO Server** | http://localhost:8002 | admin / admin123 |
| **Edge Server** | http://localhost:8001 | admin / admin123 |
| **HO Admin** | http://localhost:8002/admin/ | admin / admin123 |
| **Edge Admin** | http://localhost:8001/admin/ | admin / admin123 |
| **HO Sync Dashboard** | http://localhost:8002/promotions/compiler/ | - |
| **Edge Setup** | http://localhost:8001/setup/ | - |

---

## 🛑 Stop Servers

```bash
# Stop all
stop_all_servers.bat

# Or manually
docker-compose down
docker-compose -f docker-compose.edge.yml down
```

---

## 📝 Next Steps After Setup

1. **Create Products in HO** → http://localhost:8002/management/products/
2. **Create Promotions in HO** → http://localhost:8002/promotions/
3. **Test Sync API** → See `EDGE_SERVER_TESTING_SUMMARY.md`
4. **Implement Sync Logic** → Create management command
5. **Test POS on Edge** → http://localhost:8001/

---

## 📚 Related Documentation

- **Port Mapping**: `PORTS_MAPPING.md`
- **Full Edge Setup**: `README_EDGE_SERVER.md`
- **Sync API Guide**: `SYNC_API_DOCUMENTATION.md`
- **Testing Guide**: `EDGE_SERVER_TESTING_SUMMARY.md`

---

**Ready to sync! 🚀**

**Next:** Test the sync endpoints manually, then implement sync command.
