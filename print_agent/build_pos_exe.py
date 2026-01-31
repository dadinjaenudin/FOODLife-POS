"""
Build script for YOGYA POS Kiosk Launcher
==========================================
Creates pos.exe with embedded Python + Django + WebView

Usage:
    python build_pos_exe.py

Output:
    dist/pos.exe (main launcher)
    
Deployment structure:
    YOGYA-POS/
      ├── pos.exe                    <- Main launcher
      ├── PrintAgent.exe             <- Copy from print_agent/dist/
      ├── PrintAgentDashboard.exe    <- Copy from print_agent/dist/
      ├── print_agent_config.json    <- Printer config
      ├── db.sqlite3                 <- Database
      ├── media/                     <- Product images, etc
      └── static/                    <- Static files
"""
import PyInstaller.__main__
import os
import shutil

def build_pos_launcher():
    """Build pos.exe using PyInstaller"""
    
    print("=" * 70)
    print("[BUILD] BUILDING YOGYA POS LAUNCHER")
    print("=" * 70)
    
    # Get parent directory (project root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    print(f"[INFO] Script directory: {script_dir}")
    print(f"[INFO] Project root: {project_root}")
    
    # Clean previous builds
    if os.path.exists('build'):
        print("[*] Cleaning build folder...")
        shutil.rmtree('build')
    
    if os.path.exists('dist/pos.exe'):
        print("[*] Removing old pos.exe...")
        os.remove('dist/pos.exe')
    
    # PyInstaller arguments
    args = [
        'pos_launcher.py',
        '--name=pos',
        '--onefile',
        # '--windowed',  # Disabled for debugging - console will show
        '--icon=NONE',  # Add icon path if you have one
        
        # Include necessary Django files from parent directory
        f'--add-data={os.path.join(project_root, "pos_fnb")};pos_fnb',
        f'--add-data={os.path.join(project_root, "apps")};apps',
        f'--add-data={os.path.join(project_root, "templates")};templates',
        f'--add-data={os.path.join(project_root, "static")};static',
        f'--add-data={os.path.join(project_root, "manage.py")};.',
        f'--add-data={os.path.join(project_root, "requirements.txt")};.',
        
        # Hidden imports (Django + dependencies)
        '--hidden-import=django',
        '--hidden-import=django.contrib.admin',
        '--hidden-import=django.contrib.auth',
        '--hidden-import=django.contrib.contenttypes',
        '--hidden-import=django.contrib.sessions',
        '--hidden-import=django.contrib.messages',
        '--hidden-import=django.contrib.staticfiles',
        '--hidden-import=daphne',
        '--hidden-import=channels',
        '--hidden-import=webview',
        '--hidden-import=psycopg2',
        '--hidden-import=whitenoise',
        
        # Exclude unnecessary modules to reduce size
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=scipy',
        '--exclude-module=tkinter',
        
        # Other options
        '--noconfirm',
        '--clean',
    ]
    
    print("\n[*] Starting PyInstaller build...")
    print("[*] This may take several minutes...\n")
    
    try:
        PyInstaller.__main__.run(args)
        
        print("\n" + "=" * 70)
        print("[SUCCESS] BUILD SUCCESSFUL!")
        print("=" * 70)
        print(f"\n[INFO] Output: {os.path.abspath('dist/pos.exe')}")
        
        # Show deployment instructions
        print("\n" + "=" * 70)
        print("[DEPLOY] DEPLOYMENT INSTRUCTIONS")
        print("=" * 70)
        print("\n1. Create deployment folder: YOGYA-POS/")
        print("\n2. Copy ALL files from print_agent/dist/ to YOGYA-POS/:")
        print("   * dist/pos.exe                    (main launcher)")
        print("   * dist/PrintAgent.exe             (print service)")
        print("   * dist/PrintAgentDashboard.exe    (dashboard)")
        print("\n3. Copy these config/data files to YOGYA-POS/:")
        print("   * print_agent_config.json")
        print("   * db.sqlite3 (or create new)")
        print("   * media/ folder (if using product images)")
        print("   * static/ folder")
        
        print("\n4. Final folder structure:")
        print("   YOGYA-POS/")
        print("     |- pos.exe                      <-- Double click to start!")
        print("     ├── PrintAgent.exe")
        print("     ├── PrintAgentDashboard.exe")
        print("     ├── print_agent_config.json")
        print("     ├── db.sqlite3")
        print("     ├── media/")
        print("     └── static/")
        
        print("\n5. Run pos.exe to start POS in kiosk mode!")
        print("   - Django server auto-starts")
        print("   - Print dashboard auto-starts")
        print("   - POS opens in fullscreen")
        
        print("\n" + "=" * 70)
        
        # Calculate size
        if os.path.exists('dist/pos.exe'):
            size_mb = os.path.getsize('dist/pos.exe') / (1024 * 1024)
            print(f"\n[INFO] Executable size: {size_mb:.1f} MB")
        
    except Exception as e:
        print("\n" + "=" * 70)
        print("[FAILED] BUILD FAILED!")
        print("=" * 70)
        print(f"\nError: {e}")
        return False
    
    return True


if __name__ == '__main__':
    # Check if pywebview is installed
    try:
        import webview
    except ImportError:
        print("\n[ERROR] pywebview is not installed!")
        print("\nInstall it with:")
        print("   pip install pywebview")
        exit(1)
    
    success = build_pos_launcher()
    
    if success:
        print("\n[SUCCESS] Build completed successfully!")
    else:
        print("\n[ERROR] Build failed!")
        exit(1)
