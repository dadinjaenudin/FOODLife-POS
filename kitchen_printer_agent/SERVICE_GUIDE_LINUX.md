# Kitchen Printer Agent Service (Linux, non-root)

Panduan ini untuk menjalankan `kitchen_printer_agent` sebagai **systemd service** tanpa root.

## 1) Siapkan user service
Gunakan user non-root (contoh: `foodlife`).

Jika ingin user lain, edit:
- `kitchen-agent-python.service` → `User` dan `Group`
- `deploy_linux.sh` → bagian `useradd` dan `chown`

## 2) Deploy & Install
Jalankan di server Linux:

```bash
sudo bash kitchen_printer_agent/deploy_linux.sh
```

Script akan:
- copy file ke `/opt/foodlife/kitchen_printer_agent`
- create venv dan install dependencies
- install systemd service `kitchen-agent`

## 3) Konfigurasi Environment
Edit file env:

```bash
sudo nano /opt/foodlife/.env
```

Contoh:
```
DB_HOST=localhost
DB_PORT=5433
DB_NAME=fnb_edge_db
DB_USER=postgres
DB_PASSWORD=postgres
```

## 3b) Multi-brand Filtering (Penting)
Jika satu store punya banyak brand dan printer masing-masing, gunakan `brand_ids` pada `kitchen_agent_config.json`.

Contoh (hanya brand tertentu):
```json
"agent": {
	"name": "Kitchen-Agent-Brand-A",
	"station_codes": ["kitchen", "bar", "dessert"],
	"brand_ids": ["<brand-uuid-1>", "<brand-uuid-2>"]
}
```

Jika `brand_ids` kosong `[]`, maka agent memproses **semua brand**.

**Rekomendasi:** jalankan **1 service per brand** agar tidak campur tiket.

## 4) Start & Enable Service
```bash
sudo systemctl daemon-reload
sudo systemctl start kitchen-agent
sudo systemctl enable kitchen-agent
```

## 5) Status & Logs
```bash
sudo systemctl status kitchen-agent
sudo journalctl -u kitchen-agent -f
```

## 6) Restart / Stop
```bash
sudo systemctl restart kitchen-agent
sudo systemctl stop kitchen-agent
```

## 7) Cek berjalan dengan user non-root
```bash
ps -u foodlife -f | grep kitchen_agent
```

Jika Anda menggunakan user lain, ganti `foodlife` di semua perintah di atas.

## 8) (Opsional) Sudoers untuk Start/Stop dari POS
Jika ingin tombol **Start/Stop** di POS bisa memanggil `systemctl` tanpa password, tambahkan sudoers untuk user yang menjalankan Django (contoh: `www-data` atau `foodlife`).

1) Buat file sudoers khusus:
```bash
sudo visudo -f /etc/sudoers.d/kitchen-agent
```

2) Isi dengan (ganti `www-data` sesuai user Anda):
```
www-data ALL=NOPASSWD: /bin/systemctl start kitchen-agent
www-data ALL=NOPASSWD: /bin/systemctl stop kitchen-agent
www-data ALL=NOPASSWD: /bin/systemctl is-active kitchen-agent
```

3) Simpan, lalu pastikan permission:
```bash
sudo chmod 440 /etc/sudoers.d/kitchen-agent
```

> Catatan: gunakan user yang benar (mis. `www-data`, `foodlife`, atau user service gunicorn). Jika belum tahu user Django, cek dengan `ps aux | grep gunicorn`.
