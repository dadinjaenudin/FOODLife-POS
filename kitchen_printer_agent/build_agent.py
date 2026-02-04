"""
Build Kitchen Agent as Standalone Executable
Untuk Windows dan Linux

Requirements:
    pip install pyinstaller

Usage:
    python build_agent.py
    
Output:
    Windows: dist/KitchenAgent.exe
    Linux: dist/KitchenAgent
"""
import os
import sys
import platform
import subprocess


def build_agent():
    """Build kitchen_agent.py as executable"""
    
    print("=" * 70)
    print("BUILD KITCHEN PRINTER AGENT EXECUTABLE")
    print("=" * 70)
    print(f"Platform: {platform.system()}")
    print(f"Python: {sys.version}")
    print("=" * 70)
    
    # Detect OS
    is_windows = platform.system() == 'Windows'
    
    # Base PyInstaller command
    cmd = [
        sys.executable,
        '-m',
        'PyInstaller',
        '--onefile',
        '--name=KitchenAgent',
        '--icon=NONE',
    ]
    
    # Platform-specific settings
    if is_windows:
        print("\n[INFO] Building for Windows...")
        cmd.extend([
            '--add-data=kitchen_agent_config.json;.',
            '--collect-data=escpos',
            '--hidden-import=escpos.printer',
            '--hidden-import=escpos.printer.win32raw',
            '--hidden-import=win32print',
            '--hidden-import=psycopg2',
        ])
    else:
        print("\n[INFO] Building for Linux...")
        cmd.extend([
            '--add-data=kitchen_agent_config.json:.',
            '--collect-data=escpos',
            '--hidden-import=escpos.printer',
            '--hidden-import=escpos.printer.network',
            '--hidden-import=psycopg2',
        ])
    
    # Common options
    cmd.extend([
        '--clean',
        '--noconfirm',
        'kitchen_agent.py'
    ])
    
    print("\n[1/4] Building executable...")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ Build successful!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False
    
    print("\n[2/4] Checking output...")
    
    exe_name = 'KitchenAgent.exe' if is_windows else 'KitchenAgent'
    exe_path = os.path.join('dist', exe_name)
    
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
        print(f"✅ Executable created: {exe_path}")
        print(f"   Size: {size:.2f} MB")
    else:
        print(f"❌ Executable not found: {exe_path}")
        return False
    
    print("\n[3/4] Creating deployment package...")
    
    # Copy config to dist
    import shutil
    config_src = 'kitchen_agent_config.json'
    config_dst = os.path.join('dist', 'kitchen_agent_config.json')
    
    if os.path.exists(config_src):
        shutil.copy(config_src, config_dst)
        print(f"✅ Config copied to: {config_dst}")
    
    print("\n[4/4] Creating README...")
    
    readme_content = f"""# Kitchen Printer Agent - Standalone Executable

## Platform
Built for: {platform.system()} {platform.release()}
Python: {sys.version.split()[0]}

## Installation

### Untuk Windows:
1. Copy folder `dist` ke komputer target
2. Edit `kitchen_agent_config.json`:
   - database.host: IP/hostname database server
   - database.port: PostgreSQL port (default: 5432)
   - database.password: Password database
   - agent.station_id: ID station kitchen (1, 2, 3, dst)
   - printer.type: "network" atau "win32"
   - printer.network.host: IP printer network
   - printer.win32.name: Nama printer Windows (jika pakai USB)

3. Double-click `KitchenAgent.exe`

### Untuk Linux:
1. Copy folder `dist` ke server
2. Edit `kitchen_agent_config.json` (sama seperti Windows)
3. Jalankan:
   ```bash
   chmod +x KitchenAgent
   ./KitchenAgent
   ```

## Files Required
- KitchenAgent{'exe' if is_windows else ''} (executable)
- kitchen_agent_config.json (configuration)

## Files Generated (auto-created)
- kitchen_agent.log (application logs)

## Configuration Examples

### Network Printer (RAW ESC/POS):
```json
{{
  "printer": {{
    "type": "network",
    "brand": "HRPT",
    "network": {{
      "host": "172.17.10.36",
      "port": 9100,
      "timeout": 5
    }}
  }}
}}
```

### Windows USB Printer:
```json
{{
  "printer": {{
    "type": "win32",
    "brand": "HRPT",
    "win32": {{
      "name": "TP808",
      "enabled": true
    }}
  }}
}}
```

### Multiple Stations:
- Station 1 (Kitchen): station_id = 1
- Station 2 (Bar): station_id = 2
- Station 3 (Dessert): station_id = 3

Setiap station butuh 1 agent dengan station_id berbeda.

## Usage

### Windows:
```
KitchenAgent.exe
```

### Linux:
```bash
./KitchenAgent
```

Stop dengan: Ctrl+C

## Run as Service

### Windows (NSSM):
```powershell
# Download NSSM dari https://nssm.cc/
nssm install KitchenAgent "C:\\path\\to\\KitchenAgent.exe"
nssm start KitchenAgent
```

### Linux (Systemd):
```bash
# Create service file: /etc/systemd/system/kitchen-agent.service
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

# Enable and start
sudo systemctl enable kitchen-agent
sudo systemctl start kitchen-agent
sudo systemctl status kitchen-agent
```

## Troubleshooting

### Database Connection Error:
- Check database host/port/credentials
- Test connection: `psql -h HOST -p PORT -U USER -d DATABASE`
- Check firewall rules
- Ensure PostgreSQL allows remote connections (pg_hba.conf)

### Printer Not Printing:
1. Network printer:
   - Test connection: `telnet PRINTER_IP 9100`
   - Check printer IP is correct
   - Ensure printer is online

2. Windows USB printer:
   - Check printer name: `Get-Printer` in PowerShell
   - Ensure printer driver is installed
   - Test print from Windows

### No Tickets Processing:
- Check station_id matches database
- Check tickets status = 'new' in database
- Check agent logs: kitchen_agent.log
- Verify poll_interval is reasonable (2-5 seconds)

## Logs
Check `kitchen_agent.log` for detailed logs:
```
2026-02-04 10:30:15 [INFO] KitchenAgent: Kitchen Agent initialized
2026-02-04 10:30:15 [INFO] KitchenAgent: Station ID: 1
2026-02-04 10:30:17 [INFO] KitchenAgent: Found 2 pending ticket(s)
2026-02-04 10:30:17 [INFO] KitchenAgent: Processing ticket #KT-001 (ID: 16)
2026-02-04 10:30:18 [INFO] PrinterInterface: Printing to network: 172.17.10.36:9100
2026-02-04 10:30:18 [INFO] PrinterInterface: Print successful
2026-02-04 10:30:18 [INFO] KitchenAgent: ✓ Ticket #KT-001 printed successfully
```

## Support
For issues or questions, check:
- Application logs: kitchen_agent.log
- Database logs: Check PostgreSQL logs
- Network connectivity: ping, telnet, netstat
"""
    
    readme_path = os.path.join('dist', 'README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ README created: {readme_path}")
    
    print("\n" + "=" * 70)
    print("BUILD COMPLETE! ✅")
    print("=" * 70)
    print(f"\nDeployment package ready in: dist/")
    print(f"Executable: {exe_path}")
    print(f"Config: {config_dst}")
    print(f"README: {readme_path}")
    print("\n" + "=" * 70)
    
    return True


def main():
    """Main entry point"""
    
    # Check if PyInstaller is available
    try:
        import PyInstaller
    except ImportError:
        print("\n❌ PyInstaller not found!")
        print("Install with: pip install pyinstaller")
        sys.exit(1)
    
    # Build
    success = build_agent()
    
    if success:
        print("\n✅ Build successful! Ready to deploy.")
        sys.exit(0)
    else:
        print("\n❌ Build failed.")
        sys.exit(1)


if __name__ == '__main__':
    main()
