# Docker Architecture - HO + Edge Server Development

## 📋 Overview

Dokumentasi ini menjelaskan arsitektur Docker untuk development environment dengan dua server:
- **HO Server** (Head Office) - Sistem utama
- **Edge Server** - Sistem cabang/toko

## 📁 Struktur Direktori

```
YOGYA-Kiosk/
├── FoodBeverages-CMS/FoodBeverages-CMS/     # HO Server
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── ...
└── pos-django-htmx-main/                    # Edge Server
    ├── docker-compose.yml
    ├── Dockerfile
    └── ...
```

## 🐳 Docker Configuration

### HO Server
- **Container Name**: `fnb_ho_web`
- **Port**: `8002:8000` (host:container)
- **Database**: PostgreSQL `fnb_ho_db` (port 5432)
- **Cache**: Redis `fnb_ho_redis` (port 6379)

### Edge Server
- **Container Name**: `fnb_edge_web`
- **Port**: `8001:8000` (host:container)
- **Database**: PostgreSQL `fnb_edge_db` (port 5433)
- **Cache**: Redis `fnb_edge_redis` (port 6380)

## 🔗 Koneksi Antar Server

Edge Server terhubung ke HO Server melalui:
- **URL**: `http://host.docker.internal:8002`
- **Authentication**: Bearer token
- **Method**: POST requests
- **Fallback**: Mock data jika koneksi gagal

## 🚀 Cara Menjalankan

### 1. Start HO Server
```bash
cd "D:\YOGYA-Kiosk\FoodBeverages-CMS\FoodBeverages-CMS"
docker-compose up -d
```

### 2. Start Edge Server
```bash
cd "D:\YOGYA-Kiosk\pos-django-htmx-main"
docker-compose up -d
```

### 3. Verifikasi Koneksi
```bash
# Cek container yang berjalan
docker ps

# Cek log Edge Server
docker-compose logs edge_web -f

# Test koneksi HO Server
curl http://localhost:8002/api/v1/token/
```

## 📋 Endpoint API

### Company Dropdown
- **Frontend**: `POST /api/ho/companies/` (Edge Server)
- **Backend**: `POST /api/v1/sync/companies/` (HO Server)
- **Authentication**: Bearer token dari HO Server

### Flow:
1. Frontend (Edge) → POST `/api/ho/companies/`
2. Edge Server → GET token dari HO Server
3. Edge Server → POST `/api/v1/sync/companies/` dengan token
4. HO Server → Return companies data
5. Edge Server → Return ke frontend

## 🔧 Konfigurasi Penting

### Environment Variables (Edge Server)
```yaml
HO_API_URL=http://host.docker.internal:8002
HO_API_USERNAME=admin
HO_API_PASSWORD=admin123
```

### Docker Network Configuration
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

## 📝 Catatan Development

### Mock Data Fallback
Jika HO Server tidak accessible, Edge Server akan menggunakan mock data:
- **AVRIL COMPANY (AVRIL)**
- **DEMO COMPANY (DEMO)**

### Logging
- Enable logging untuk debugging koneksi
- Monitor `docker-compose logs edge_web -f`
- Cek error `[HO API] Error` untuk troubleshooting

### Port Management
- HO Server: 8002 (web), 5432 (db), 6379 (redis)
- Edge Server: 8001 (web), 5433 (db), 6380 (redis)
- Tidak ada conflict antar port

## 🛠️ Troubleshooting

### Common Issues
1. **host.docker.internal tidak accessible**
   - Pastikan `extra_hosts` configuration ada
   - Restart container setelah perubahan

2. **Port conflict**
   - Cek dengan `netstat -ano | findstr :PORT`
   - Stop container yang conflict

3. **Database connection failed**
   - Pastikan container database healthy
   - Cek healthcheck status

### Commands
```bash
# Restart specific service
docker-compose restart edge_web

# Rebuild container
docker-compose up -d --build edge_web

# Clean up containers
docker-compose down
docker system prune -f
```

## 🔄 Development Workflow

1. **Start Environment**: HO Server → Edge Server
2. **Development**: Edit code di direktori masing-masing
3. **Testing**: Akses `http://localhost:8001/setup/`
4. **Debugging**: Monitor log dan test API endpoints
5. **Shutdown**: `docker-compose down` di masing-masing direktori

## 📚 References

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Networking](https://docs.docker.com/network/)
- [Django Docker Deployment](https://docs.djangoproject.com/en/stable/howto/deployment/wsgi/gunicorn/)
