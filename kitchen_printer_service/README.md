# Kitchen Printer Service

**Stateless, production-ready ESC/POS print service for F&B POS systems**

## 🎯 Overview

Kitchen Printer Service adalah standalone Python service yang:
- Polls database untuk kitchen tickets dengan status='new'
- Routes tickets ke printer yang tepat berdasarkan station code
- Prints menggunakan ESC/POS protocol ke network printers
- Handles retry, failure, dan monitoring
- Exposes health check endpoint

## 📋 Architecture

```
┌─────────────┐
│   Django    │ (POS creates tickets)
│   Backend   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ PostgreSQL  │ (kitchen_kitchenticket table)
│  Database   │
└──────┬──────┘
       ▲
       │ (polls every 2s)
       │
┌──────┴──────┐
│  Kitchen    │
│  Printer    │◄─── Health Check (:9100/health)
│  Service    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  ESC/POS    │ (192.168.1.100:9100)
│  Printer    │
└─────────────┘
```

## 🚀 Features

### Core Functionality
✅ **Stateless** - No local state, database is source of truth
✅ **Idempotent** - Safe to restart anytime, no duplicate prints
✅ **Retry Logic** - Automatic retry with max attempts
✅ **Health Check** - HTTP endpoint on port 9100
✅ **Audit Trail** - All actions logged to database
✅ **Multi-Station** - Supports BAR, KITCHEN, DESSERT, etc.
✅ **Backup Printers** - Priority-based printer routing

### Production Ready
✅ Handles printer offline gracefully
✅ Handles network timeouts
✅ Graceful shutdown on SIGTERM/SIGINT
✅ Comprehensive logging
✅ Docker containerized
✅ Health check for monitoring

## 📁 Project Structure

```
kitchen_printer_service/
├── __init__.py          # Package init
├── config.py            # Configuration from ENV
├── database.py          # PostgreSQL interactions
├── printer.py           # ESC/POS printing logic
├── health.py            # Health check HTTP server
├── main.py              # Main service loop
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container definition
└── README.md            # This file
```

## 🔧 Installation

### 1. Install Dependencies

```bash
cd kitchen_printer_service
pip install -r requirements.txt
```

### 2. Configure Environment

Set these environment variables:

```bash
# Database
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=fnb_edge_db
export DB_USER=postgres
export DB_PASSWORD=postgres123

# Service
export POLL_INTERVAL=2              # Poll every 2 seconds
export MAX_TICKETS_PER_POLL=10      # Process max 10 tickets per poll
export MAX_PRINT_RETRIES=3          # Max 3 retry attempts
export HEALTH_CHECK_PORT=9100       # Health check port
export LOG_LEVEL=INFO               # Logging level
```

### 3. Run Service

```bash
python main.py
```

## 🐳 Docker Deployment

### Build & Run

```bash
# Build image
docker build -t kitchen-printer-service .

# Run container
docker run -d \
  --name kitchen_printer_service \
  -p 9100:9100 \
  -e DB_HOST=edge_db \
  -e DB_PORT=5432 \
  -e DB_NAME=fnb_edge_db \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres123 \
  kitchen-printer-service
```

### Docker Compose

Service sudah terintegrasi di `docker-compose.yml`:

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f kitchen_printer_service

# Restart service
docker-compose restart kitchen_printer_service
```

## 📊 Monitoring

### Health Check Endpoint

```bash
curl http://localhost:9100/health
```

Response:
```json
{
  "status": "healthy",
  "service": "Kitchen Printer Service",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "uptime_formatted": "1h 0m 0s",
  "database": "connected",
  "last_poll": "2026-02-04T14:30:00",
  "metrics": {
    "tickets_processed": 145,
    "tickets_failed": 2,
    "success_rate": 98.64,
    "pending_tickets": 3,
    "printed_today": 142,
    "failed_tickets": 2
  }
}
```

### Metrics Endpoint

```bash
curl http://localhost:9100/metrics
```

### Logs

```bash
# Docker logs
docker-compose logs -f kitchen_printer_service

# Service logs (if running locally)
tail -f kitchen_printer_service.log
```

## 🧪 Testing

### Test Database Connection

```bash
python test_kitchen_printer_service.py
```

### Manual Test Flow

1. Create ticket via Django:
```python
from apps.kitchen.services import create_kitchen_tickets
from apps.pos.models import Bill

bill = Bill.objects.get(bill_number='TBL01-001')
tickets = create_kitchen_tickets(bill)
```

2. Check service logs:
```bash
docker-compose logs -f kitchen_printer_service
```

3. Verify ticket status:
```python
from apps.kitchen.models import KitchenTicket

ticket = KitchenTicket.objects.get(id=1)
print(ticket.status)  # Should be 'printed'
```

## 📖 How It Works

### Data Flow

1. **POS creates order** → Django creates `kitchen_kitchenticket` with status='new'
2. **Service polls database** → Fetches tickets with status='new'
3. **Resolve printer** → Looks up active printer for station code
4. **Mark as printing** → Updates status to 'printing', locks ticket
5. **Print via ESC/POS** → Sends formatted data to network printer
6. **Update status** → Marks as 'printed' or 'failed'
7. **Log action** → Writes audit trail to `kitchen_kitchenlog`

### Retry Logic

- Ticket starts with `print_attempts=0`, `max_retries=3`
- On print failure:
  - If `print_attempts < max_retries`: Reset to status='new' (will retry)
  - If `print_attempts >= max_retries`: Mark as status='failed' (manual intervention needed)

### Printer Routing

Printers are selected based on:
1. `station_code` match (e.g., 'kitchen', 'bar')
2. `brand_id` match (multi-tenant)
3. `is_active=true` filter
4. `priority ASC` (1=primary, 2=backup)

## 🔍 Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs kitchen_printer_service

# Common issues:
# 1. Database not ready → Wait for edge_db to be healthy
# 2. Port 9100 in use → Change HEALTH_CHECK_PORT
```

### Tickets not printing

```bash
# 1. Check service is running
curl http://localhost:9100/health

# 2. Check pending tickets
docker exec -it fnb_edge_db psql -U postgres -d fnb_edge_db -c "SELECT id, status FROM kitchen_kitchenticket WHERE status='new';"

# 3. Check printer config
docker exec -it fnb_edge_db psql -U postgres -d fnb_edge_db -c "SELECT * FROM kitchen_stationprinter WHERE is_active=true;"

# 4. Test printer connection
ping 192.168.1.100
telnet 192.168.1.100 9100
```

### Tickets stuck in 'printing'

This means service crashed mid-print. Reset manually:

```sql
UPDATE kitchen_kitchenticket 
SET status='new' 
WHERE status='printing';
```

## 📚 Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `edge_db` | PostgreSQL hostname |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `fnb_edge_db` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `postgres123` | Database password |
| `POLL_INTERVAL` | `2` | Polling interval (seconds) |
| `MAX_TICKETS_PER_POLL` | `10` | Max tickets per poll |
| `MAX_PRINT_RETRIES` | `3` | Max retry attempts |
| `RETRY_DELAY_SECONDS` | `5` | Delay between retries |
| `HEALTH_CHECK_PORT` | `9100` | Health check port |
| `LOG_LEVEL` | `INFO` | Logging level |

## 🛠️ Development

### Local Development

```bash
# 1. Start database
docker-compose up -d edge_db

# 2. Run service locally
export DB_HOST=localhost
export DB_PORT=5433
python kitchen_printer_service/main.py
```

### Adding New Features

1. Update relevant module (`database.py`, `printer.py`, etc.)
2. Test locally
3. Rebuild Docker image
4. Deploy

## 📝 Best Practices

### DO's ✅
- Always check health endpoint before deployment
- Monitor failed tickets daily
- Test printer connectivity before adding to system
- Use backup printers (priority 2+)
- Review logs regularly

### DON'Ts ❌
- Don't print directly from POS
- Don't hardcode printer IPs in code
- Don't ignore failed tickets
- Don't run multiple instances (causes duplicate prints)

## 📄 License

Internal use only - FoodLife POS System

## 👥 Contact

For issues or questions, contact the development team.
