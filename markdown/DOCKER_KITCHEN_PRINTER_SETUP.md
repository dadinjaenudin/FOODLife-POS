# Docker + Kitchen Printer Agent — Setup Guide

> Panduan setup Docker agar Kitchen Printer Agent bisa mencetak ke network printer di LAN.
> Berlaku untuk **Windows (Docker Desktop)** dan **Linux (Docker Engine)**.

---

## Daftar Isi

1. [Masalah](#1-masalah)
2. [Arsitektur](#2-arsitektur)
3. [Setup Windows (Docker Desktop)](#3-setup-windows-docker-desktop)
4. [Setup Linux (Docker Engine)](#4-setup-linux-docker-engine)
5. [Verifikasi](#5-verifikasi)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Masalah

Kitchen Printer Agent di Docker perlu mencetak ke **network printer** di LAN via TCP socket (IP:9100).

**Problem**: Docker secara default membuat bridge network `docker0` di subnet `172.17.0.0/16`. Jika printer LAN menggunakan IP di range yang sama (contoh: `172.17.10.36`, `172.17.10.114`), maka traffic ke printer **di-capture oleh Docker bridge** dan tidak pernah sampai ke LAN fisik.

```
# Routing table di Docker host/VM:
172.17.0.0/16  →  docker0    ← Docker bridge (CAPTURES traffic!)
default        →  eth0       ← Gateway ke LAN fisik

# Akibatnya:
Container → 172.17.10.36:9100 → docker0 → dead end (timeout)
#                                  ↑ harusnya ke LAN, tapi ketangkap docker0
```

**Solusi** (2 langkah):
1. Ubah Docker default bridge subnet (`bip`) agar tidak conflict dengan LAN
2. Set explicit subnet untuk `pos_network` di `docker-compose.yml`

---

## 2. Arsitektur

```
┌─────────────────────────────────────────────────────┐
│  Docker Host (Windows/Linux)                        │
│                                                     │
│  ┌───────────────────────────┐                      │
│  │ kitchen_agent             │                      │
│  │ (network_mode: host)      │                      │
│  │                           │   TCP socket         │
│  │ kitchen_agent.py ─────────┼──────────────────►   │
│  │   DB: localhost:5433      │   172.17.10.36:9100  │
│  │   Health: 0.0.0.0:5001   │   (LAN printer)      │
│  └───────────────────────────┘                      │
│                                                     │
│  ┌─────────── pos_network (172.28.0.0/16) ───────┐  │
│  │ edge_db    edge_redis   edge_web   edge_minio │  │
│  │ :5432      :6379        :8000      :9000      │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  docker0: 172.30.0.0/16 (changed from 172.17.x.x)  │
└─────────────────────────────────────────────────────┘
         │                              │
    Port mapping                    LAN (physical)
    5433→5432 (DB)              ┌─────────────────┐
    8001→8000 (Web)             │ Kitchen Printer  │
    5001 (Agent health)         │ 172.17.10.36     │
                                │ :9100            │
                                └─────────────────┘
```

**Kenapa `kitchen_agent` pakai `network_mode: host`?**
- Butuh akses langsung ke LAN untuk reach printer via TCP socket
- Service lain (Django, Celery, Redis) tidak perlu akses LAN langsung, cukup bridge network

---

## 3. Setup Windows (Docker Desktop)

### 3.1 Ubah Docker Bridge Subnet

1. Buka **Docker Desktop** → klik **gear icon** (Settings)
2. Pilih **Docker Engine** di menu kiri
3. Edit JSON config, tambahkan `"bip"`:

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "bip": "172.30.0.1/16"
}
```

4. Klik **Apply & Restart**
5. Tunggu Docker Desktop restart (semua container akan mati)

### 3.2 Restart Services

```bash
cd D:\YOGYA-FOODLIFE\FoodLife-POS
docker compose down        # Hapus container & network lama
docker compose up -d       # Buat ulang dengan subnet baru
```

### 3.3 Verifikasi Subnet

```bash
# Pastikan pos_network di 172.28.x.x (bukan 172.17.x.x)
docker network inspect foodlife-pos_pos_network --format "{{.IPAM.Config}}"
# Expected: [{172.28.0.0/16 ...}]

# Pastikan docker0 bridge di 172.30.x.x
docker network inspect bridge --format "{{.IPAM.Config}}"
# Expected: [{172.30.0.0/16 ...}]
```

### Catatan Windows

- Docker Desktop menjalankan container di **Linux VM** (WSL2/Hyper-V)
- `network_mode: host` = share VM network, bukan Windows network
- Traffic ke printer: Container → VM → NAT → Windows host → LAN → Printer
- `host.docker.internal` tersedia untuk container reach Windows host

---

## 4. Setup Linux (Docker Engine)

### 4.1 Ubah Docker Bridge Subnet

```bash
# Edit daemon.json (buat file jika belum ada)
sudo nano /etc/docker/daemon.json
```

Isi:

```json
{
  "bip": "172.30.0.1/16"
}
```

Restart Docker:

```bash
sudo systemctl restart docker
```

### 4.2 Start Services

```bash
cd /opt/foodlife-pos   # atau path project di server
docker compose down
docker compose up -d
```

### 4.3 Verifikasi Subnet

```bash
# Cek docker0 subnet
ip addr show docker0
# Expected: inet 172.30.0.1/16

# Cek pos_network
docker network inspect foodlife-pos_pos_network --format "{{.IPAM.Config}}"
# Expected: [{172.28.0.0/16 ...}]

# Pastikan TIDAK ADA bridge di 172.17.x.x
ip route | grep 172.17
# Expected: kosong (tidak ada output)
```

### Catatan Linux

- `network_mode: host` = **benar-benar share host network** (no VM, no NAT)
- Traffic ke printer: Container → Host network stack → LAN → Printer (langsung!)
- Performance lebih baik dibanding Windows (tidak ada VM layer)
- Port 5001 langsung terbuka di host (tidak perlu port mapping)

---

## 5. Verifikasi

### 5.1 Cek Container Running

```bash
docker compose ps
```

Expected output:
```
NAME                   STATUS
fnb_edge_db            running (healthy)
fnb_edge_redis         running (healthy)
fnb_edge_minio         running (healthy)
fnb_edge_web           running
fnb_edge_celery_worker running
fnb_edge_celery_beat   running
fnb_kitchen_agent      running
```

### 5.2 Cek Kitchen Agent Logs

```bash
docker logs fnb_kitchen_agent --tail 20
```

Expected:
```
Database is ready!
============================================================
KITCHEN PRINTER AGENT
Version 1.0.0
============================================================
[INFO] Initializing agent...
[DEBUG] Connecting to database:
  Host: localhost
  Port: 5433
...
```

### 5.3 Test Koneksi Printer dari Container

```bash
# Ganti IP dengan IP printer di LAN
docker exec fnb_kitchen_agent nc -zv -w 3 172.17.10.36 9100
```

Expected: `Connection to 172.17.10.36 9100 port [tcp/*] succeeded!`

Jika timeout → lihat [Troubleshooting](#6-troubleshooting).

### 5.4 Test Health Endpoint

```bash
# Dari host
curl http://localhost:5001/health
```

Expected:
```json
{
  "status": "ok",
  "agent_name": "Kitchen-Agent-1",
  "uptime_seconds": 123,
  "tickets_processed": 0,
  "stations": [1, 2, 3]
}
```

### 5.5 Test dari POS UI

1. Buka POS di browser: `http://localhost:8001/pos/`
2. Di sidebar, Kitchen Printer widget harus **hijau** (agent online)
3. Klik widget → flyout menunjukkan agent name, uptime, printer list

---

## 6. Troubleshooting

### Printer timeout dari container

**Gejala**: `nc -zv -w 3 <IP> 9100` timeout dari container tapi sukses dari host.

**Diagnosa**:
```bash
# Cek routing table di container
docker exec fnb_kitchen_agent cat /proc/net/route

# Cari apakah ada route 172.17.x.x ke bridge interface
# Jika ada "docker0" atau "br-xxxx" di 172.17.0.0/16 → subnet conflict!
```

**Fix**: Pastikan `bip` sudah diset dan Docker sudah di-restart:

```bash
# Windows: Docker Desktop → Settings → Docker Engine → cek "bip"
# Linux:
cat /etc/docker/daemon.json    # harus ada "bip": "172.30.0.1/16"
sudo systemctl restart docker
docker compose down && docker compose up -d
```

### Printer timeout dari host juga

Jika printer tidak bisa direach dari host (bukan Docker):
- Printer mati / offline
- IP printer salah (cek di `/kitchen/printers/manage/`)
- Firewall block port 9100
- Printer dan server beda VLAN/subnet tanpa routing

### Kitchen Agent crash loop

```bash
docker logs fnb_kitchen_agent --tail 50
```

Kemungkinan:
- **DB connection refused**: Pastikan `edge_db` healthy dan port 5433 di-expose
- **Port 5001 already in use**: Proses lain di host pakai port 5001

### Widget menunjukkan agent offline (merah)

Cek dari browser console (F12):
```
GET http://localhost:5001/health → ERR_CONNECTION_REFUSED?
```

Kemungkinan:
- Kitchen agent container tidak running → `docker compose up -d kitchen_agent`
- Port 5001 tidak tersedia → `docker logs fnb_kitchen_agent`
- Browser di mesin berbeda → ganti URL ke IP server (bukan localhost)

### `pos_network` conflict setelah Docker restart

Jika `docker compose up` gagal karena subnet conflict:

```bash
# Hapus semua network yang tidak dipakai
docker network prune

# Lalu coba lagi
docker compose up -d
```

---

## Quick Reference

### File yang relevan

| File | Fungsi |
|------|--------|
| `docker-compose.yml` | Service definitions, network config |
| `kitchen_printer_agent/kitchen_agent.py` | Agent daemon + health server |
| `kitchen_printer_agent/kitchen_agent_config.json` | Agent config (polling, timeout) |
| `apps/pos/views.py` → `kitchen_agent_status` | Django view: agent health proxy |
| `templates/pos/partials/main/kitchen_printer_widget.html` | POS UI widget |

### Port mapping

| Port | Service | Keterangan |
|------|---------|------------|
| 5433 | PostgreSQL (edge_db) | Host → container 5432 |
| 6380 | Redis (edge_redis) | Host → container 6379 |
| 8001 | Django (edge_web) | Host → container 8000 |
| 9002 | MinIO API (edge_minio) | Host → container 9000 |
| 9003 | MinIO Console | Host → container 9001 |
| 5001 | Kitchen Agent health | Langsung (host network) |

### Docker daemon.json

```json
{
  "bip": "172.30.0.1/16"
}
```

| OS | Lokasi |
|----|--------|
| Windows | Docker Desktop → Settings → Docker Engine |
| Linux | `/etc/docker/daemon.json` |

### Environment variables (kitchen_agent)

| Variable | Default | Keterangan |
|----------|---------|------------|
| `DB_HOST` | localhost | Database host (localhost karena host network) |
| `DB_PORT` | 5433 | Port host-mapped PostgreSQL |
| `DB_NAME` | fnb_edge_db | Database name |
| `DB_USER` | postgres | Database user |
| `DB_PASSWORD` | postgres123 | Database password |
| `AGENT_NAME` | Kitchen-Agent-1 | Nama agent (tampil di widget) |
| `STATION_IDS` | 1,2,3 | Station IDs yang di-handle |
| `HEALTH_SERVER_PORT` | 5001 | Port HTTP health server |
