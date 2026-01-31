"""
Build Print Agent as Standalone Executable
No Python installation required on target machine

Requirements:
    pip install pyinstaller

Usage:
    python build_executable.py
    
Output:
    dist/PrintAgent.exe (Windows executable)
"""
import os
import sys
import subprocess

def build_agent():
    """Build agent_v2.py as executable"""
    
    print("=" * 60)
    print("BUILD PRINT AGENT EXECUTABLE")
    print("=" * 60)
    
    # PyInstaller command (use python -m to avoid PATH issues)
    cmd = [
        sys.executable,                 # Use current Python interpreter
        '-m',
        'PyInstaller',
        '--onefile',                    # Single executable file
        '--name=PrintAgent',            # Executable name
        '--icon=NONE',                  # No icon (or add your .ico file)
        '--add-data=print_agent_config.json;.',  # Include config
        '--collect-data=escpos',        # Include escpos data files (capabilities.json)
        '--hidden-import=escpos.printer',
        '--hidden-import=escpos.printer.win32raw',
        '--hidden-import=win32print',
        '--hidden-import=requests',
        '--clean',                      # Clean cache
        '--noconfirm',                  # Overwrite without asking
        'agent_v2.py'                   # Source file
    ]
    
    print("\n[1/3] Building executable...")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ Build successful!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed: {e}")
        return False
    
    print("\n[2/3] Checking output...")
    exe_path = os.path.join('dist', 'PrintAgent.exe')
    
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
        print(f"✅ Executable created: {exe_path}")
        print(f"   Size: {size:.2f} MB")
    else:
        print(f"❌ Executable not found: {exe_path}")
        return False
    
    print("\n[3/3] Creating deployment package...")
    
    # Create README for distribution
    readme_content = """# Print Agent - Standalone Executable

## Installation (Komputer POS tanpa Python)

1. Copy folder ini ke komputer POS
2. Edit `print_agent_config.json` sesuai kebutuhan
3. Double-click `PrintAgent.exe` untuk menjalankan

## Files Required
- PrintAgent.exe (main executable)
- print_agent_config.json (configuration)

## Files Generated (auto-created)
- printed_jobs.json (job history)
- print_agent.log (logs)

## Configuration
Edit `print_agent_config.json`:
- terminal_id: ID terminal (e.g., "POS-001")
- printer.name: Nama printer Windows (e.g., "TP808")
- printer.brand: Brand printer (HRPT, Epson, XPrinter)

## Usage
Double-click PrintAgent.exe atau jalankan dari Command Prompt:
```
PrintAgent.exe
```

Stop dengan: Ctrl+C

## Troubleshooting
1. Jika error "printer not found":
   - Check printer name di Windows Devices & Printers
   - Update `printer.name` di config

2. Jika error "server connection":
   - Check `server.url` di config
   - Pastikan Django server running

3. Logs tersimpan di: print_agent.log
"""
    
    with open('dist/README.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    # Copy config to dist
    import shutil
    shutil.copy('print_agent_config.json', 'dist/')
    
    print("✅ Deployment package ready in 'dist/' folder")
    print("\n" + "=" * 60)
    print("DEPLOYMENT INSTRUCTIONS:")
    print("=" * 60)
    print("1. Copy entire 'dist/' folder to POS computer")
    print("2. Edit print_agent_config.json")
    print("3. Double-click PrintAgent.exe")
    print("=" * 60)
    
    return True


def build_dashboard():
    """Build dashboard.py as executable"""
    
    print("\n" + "=" * 60)
    print("BUILD DASHBOARD EXECUTABLE")
    print("=" * 60)
    
    cmd = [
        sys.executable,                 # Use current Python interpreter
        '-m',
        'PyInstaller',
        '--onefile',
        '--name=PrintAgentDashboard',
        '--icon=NONE',
        '--add-data=templates;templates',
        '--add-data=print_agent_config.json;.',
        '--collect-data=escpos',        # Include escpos data files
        '--hidden-import=flask',
        '--hidden-import=escpos.printer',
        '--hidden-import=escpos.printer.win32raw',
        '--hidden-import=psutil',
        '--clean',
        '--noconfirm',
        'dashboard.py'
    ]
    
    print("\n[1/2] Building dashboard executable...")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Dashboard build successful!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Dashboard build failed: {e}")
        return False
    
    print("\n[2/2] Checking output...")
    exe_path = os.path.join('dist', 'PrintAgentDashboard.exe')
    
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"✅ Dashboard executable: {exe_path}")
        print(f"   Size: {size:.2f} MB")
        print(f"   Access: http://localhost:5050")
    else:
        print(f"❌ Dashboard executable not found")
        return False
    
    return True


if __name__ == '__main__':
    print("\n🚀 Starting build process...\n")
    
    # Check if pyinstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("❌ PyInstaller not installed!")
        print("Install with: pip install pyinstaller")
        sys.exit(1)
    
    # Build agent
    success_agent = build_agent()
    
    # Build dashboard (optional)
    print("\n")
    build_dashboard_choice = input("Build dashboard executable juga? (y/n): ").lower()
    
    if build_dashboard_choice == 'y':
        success_dashboard = build_dashboard()
    else:
        print("⏭️  Skipping dashboard build")
    
    print("\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print("=" * 60)
    
    if success_agent:
        print("✅ Print Agent: dist/PrintAgent.exe")
    
    print("\n📦 Ready for deployment!")
    print("=" * 60)
