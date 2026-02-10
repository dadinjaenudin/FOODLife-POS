# Kitchen Printer Agent

Autonomous agent untuk kitchen ticket printing. Dapat di-compile menjadi standalone executable untuk Windows dan Linux.

## Features

✅ **Database Polling** - Monitor kitchen tickets dari PostgreSQL  
✅ **Network Printer** - Support RAW ESC/POS via TCP/IP (port 9100)  
✅ **Windows USB Printer** - Support Win32Raw untuk printer USB  
✅ **Multi-Station** - Support multiple kitchen stations  
✅ **Auto-Retry** - Retry logic untuk failed tickets  
✅ **Standalone Executable** - Compile ke .exe (Windows) atau binary (Linux)  
✅ **Printer Profiles** - Support HRPT, Epson, XPrinter  
✅ **Comprehensive Logging** - Detailed logs untuk troubleshooting  

## Quick Start

### 1. Install Dependencies

```bash
python -m pip install psycopg2-binary python-escpos python-dotenv

```

### 2. Configure

Edit `kitchen_agent_config.json`:

```json
{
  "agent": {
    "station_id": 1
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "database": "fnb_edge_db",
    "user": "postgres",
    "password": "postgres"
  },
  "printer": {
    "type": "network",
    "brand": "HRPT",
    "network": {
      "host": "172.17.10.36",
      "port": 9100
    }
  }
}
```

### 3. Run Agent

```bash
python kitchen_agent.py
```

## Build Executable

### For Windows:

```bash
pip install pyinstaller
python build_agent.py
```

Output: `dist/KitchenAgent.exe`

### For Linux:

```bash
pip install pyinstaller
python build_agent.py
```

Output: `dist/KitchenAgent`

## Configuration

### Network Printer (Recommended)

```json
{
  "printer": {
    "type": "network",
    "brand": "HRPT",
    "network": {
      "host": "172.17.10.36",
      "port": 9100,
      "timeout": 5
    }
  }
}
```

**Advantages:**
- No driver installation needed
- Can be accessed from any machine
- Works from Docker, Windows, Linux
- Simple troubleshooting (telnet test)

### Windows USB Printer

```json
{
  "printer": {
    "type": "win32",
    "brand": "HRPT",
    "win32": {
      "name": "TP808",
      "enabled": true
    }
  }
}
```

**Requirements:**
- Windows printer driver installed
- Agent must run on same PC as printer
- Cannot run from Docker

### Multiple Stations

Run multiple agents with different `station_id`:

**Kitchen Station (ID: 1):**
```json
{
  "agent": {
    "station_id": 1
  }
}
```

**Bar Station (ID: 2):**
```json
{
  "agent": {
    "station_id": 2
  }
}
```

Each agent monitors only its assigned station.

## Printer Brands

### HRPT (TP808)
- Limited ESC/POS command set
- Uses GS ! commands for font sizing
- Requires specific command sequence

### Epson (TM-series)
- Full ESC/POS support
- Uses ESC ! commands
- Most compatible

### XPrinter
- Similar to Epson
- Full ESC/POS support

## Architecture

```
┌─────────────────┐
│   Django POS    │
│  (Create Order) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│ kitchen_ticket  │
│  status='new'   │
└────────┬────────┘
         │
         ▼ (polling every 2s)
┌─────────────────┐
│ Kitchen Agent   │
│  - Fetch new    │
│  - Format ESC   │
│  - Print        │
│  - Mark printed │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Printer        │
│ Network/USB     │
└─────────────────┘
```

## Database Schema

Agent monitors these tables:

**kitchen_kitchenticket:**
- id, ticket_number, order_number
- station_id, status ('new', 'printing', 'printed', 'failed')
- printer_ip, created_at, printed_at

**kitchen_kitchenticketitem:**
- ticket_id, product_id, quantity, notes

**kitchen_kitchenticketlog:**
- ticket_id, action, message, timestamp

## Workflow

1. **Poll Database** - Every 2 seconds, fetch tickets WHERE status='new'
2. **Mark Printing** - Update status to 'printing'
3. **Format Ticket** - Generate ESC/POS commands based on printer profile
4. **Print** - Send to network socket or Win32Raw
5. **Mark Printed** - Update status to 'printed', set printed_at
6. **Log Action** - Insert log entry to kitchen_kitchenticketlog

## Testing

### Test Database Connection

```python
python -c "import psycopg2; conn = psycopg2.connect(host='localhost', port=5432, database='fnb_edge_db', user='postgres', password='postgres'); print('OK')"
```

### Test Network Printer

```bash
python test_printer.py --ip 172.17.10.36 --port 9100
```

### Test Agent (Dry Run)

```bash
python kitchen_agent.py
```

Watch logs in `kitchen_agent.log`

## Deployment

### Windows Service (NSSM)

1. Download NSSM: https://nssm.cc/
2. Install service:

```powershell
nssm install KitchenAgent "C:\kitchen_agent\KitchenAgent.exe"
nssm set KitchenAgent AppDirectory "C:\kitchen_agent"
nssm set KitchenAgent DisplayName "Kitchen Printer Agent"
nssm set KitchenAgent Description "Kitchen ticket printing service"
nssm start KitchenAgent
```

3. Check status:

```powershell
nssm status KitchenAgent
Get-Service KitchenAgent
```

### Linux Systemd

1. Create service file: `/etc/systemd/system/kitchen-agent.service`

```ini
[Unit]
Description=Kitchen Printer Agent
After=network.target postgresql.service

[Service]
Type=simple
User=kitchen
WorkingDirectory=/opt/kitchen_agent
ExecStart=/opt/kitchen_agent/KitchenAgent
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kitchen-agent
sudo systemctl start kitchen-agent
sudo systemctl status kitchen-agent
```

3. View logs:

```bash
sudo journalctl -u kitchen-agent -f
```

## Troubleshooting

### Database Connection Failed

**Symptoms:**
```
[ERROR] DatabaseManager: Database connection failed: connection refused
```

**Solutions:**
1. Check database is running: `docker ps | grep edge_db`
2. Check PostgreSQL port: `netstat -an | findstr 5432`
3. Test connection: `psql -h localhost -p 5432 -U postgres -d fnb_edge_db`
4. Check pg_hba.conf allows connections
5. Verify config.json has correct credentials

### Printer Not Printing

**Network Printer:**

1. Test connection:
   ```bash
   telnet 172.17.10.36 9100
   ```
   Should connect without errors.

2. Test raw print:
   ```bash
   python test_printer.py
   ```
   Should print test ticket.

3. Check logs:
   ```
   [ERROR] PrinterInterface: Network print failed: [Errno 113] No route to host
   ```
   - Printer is offline or unreachable
   - Check IP address
   - Check network/firewall

**Windows USB Printer:**

1. Check printer name:
   ```powershell
   Get-Printer | Where-Object {$_.Name -like "*TP808*"}
   ```

2. Verify driver installed:
   ```powershell
   Get-PrinterDriver
   ```

3. Test Windows print:
   ```powershell
   "TEST" | Out-Printer -Name "TP808"
   ```

### No Tickets Being Processed

**Check agent logs:**
```bash
tail -f kitchen_agent.log
```

**Verify tickets exist:**
```sql
SELECT * FROM kitchen_kitchenticket 
WHERE status = 'new' AND station_id = 1
ORDER BY created_at DESC;
```

**Check station_id:**
- Agent config: `"station_id": 1`
- Database ticket: `station_id = 1`
- Must match!

**Check polling:**
- Default interval: 2 seconds
- Increase log level to DEBUG in config
- Should see "Found X pending ticket(s)" in logs

### Tickets Stuck in 'printing' Status

**Reset stuck tickets:**
```sql
UPDATE kitchen_kitchenticket 
SET status = 'new' 
WHERE status = 'printing' AND created_at < NOW() - INTERVAL '5 minutes';
```

**Prevent:**
- Ensure agent runs continuously
- Use Windows Service or systemd
- Monitor agent process

## Performance

### Recommended Settings

**Single Station:**
- poll_interval: 2 seconds
- max_tickets_per_poll: 10

**Multiple Stations (3-5):**
- poll_interval: 1 second
- max_tickets_per_poll: 5

**High Volume (>100 orders/hour):**
- poll_interval: 1 second
- max_tickets_per_poll: 20
- Consider dedicated database connection per agent

### Resource Usage

**Memory:** ~30-50 MB per agent  
**CPU:** <1% idle, 5-10% when printing  
**Network:** Minimal (database queries + printer data)  
**Disk:** Log files rotate at 10 MB

## Monitoring

### Health Check

Agent logs heartbeat every 30 seconds:
```
[INFO] KitchenAgent: Station 1 - Running (uptime: 3600s)
```

### Metrics

Track in database:
- Tickets printed per hour
- Average print time
- Failed ticket rate
- Agent uptime

### Alerts

Monitor for:
- Agent process stopped
- High failed ticket rate (>5%)
- Printer offline errors
- Database connection errors

## Support

**Logs Location:**
- Application: `kitchen_agent.log`
- Database: PostgreSQL logs
- Windows Service: Event Viewer
- Linux Service: `journalctl -u kitchen-agent`

**Common Issues:**
1. Database connection → Check credentials, firewall
2. Printer not responding → Test telnet, check IP
3. No tickets processing → Verify station_id matches
4. Stuck tickets → Reset status to 'new'

## Version History

**1.0.0** (2026-02-04)
- Initial release
- Database polling
- Network printer support
- Windows USB printer support
- Multi-station support
- Executable build support
- Comprehensive logging
