"""
YOGYA POS Kiosk Launcher
========================
Integrated launcher that starts Django server, Print Dashboard, and opens POS in kiosk window.

Features:
- Auto-start Django server (background)
- Auto-start Print Agent Dashboard (background)
- Fullscreen kiosk mode
- Auto-cleanup on exit
- Single instance lock (prevents multiple instances)
"""
import os
import sys
import time
import subprocess
import atexit
import webbrowser
import socket

# Try to import webview, but fallback to webbrowser if not available
try:
    import webview
    WEBVIEW_AVAILABLE = True
except ImportError:
    print("⚠️  pywebview not available, using default browser instead")
    WEBVIEW_AVAILABLE = False
from threading import Thread

# Global process trackers
django_process = None
dashboard_process = None
browser_opened = False
lock_socket = None


def get_app_dir():
    """Get application directory (works for both .py and .exe)"""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        # PyInstaller extracts files to sys._MEIPASS temporary directory
        return sys._MEIPASS
    else:
        # Running as script from print_agent/ folder
        # Need to go up one level to reach project root
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def acquire_single_instance_lock():
    """Acquire single instance lock using socket binding to prevent multiple instances"""
    global lock_socket
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Try to bind to a specific port to ensure only one instance
        lock_socket.bind(('127.0.0.1', 47200))
        return True
    except socket.error:
        # Port already in use - another instance is running
        return False


def is_django_running():
    """Check if Django server is already running on port 8000"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(0.5)
        result = sock.connect_ex(('127.0.0.1', 8000))
        sock.close()
        return result == 0
    except:
        return False


def start_django_server():
    """Start Django development server in background"""
    global django_process
    
    app_dir = get_app_dir()
    manage_py = os.path.join(app_dir, 'manage.py')
    
    if not os.path.exists(manage_py):
        print(f"⚠️  manage.py not found in {app_dir}")
        return False
    
    print("[*] Starting Django server...")
    
    # Set environment variables for SQLite mode
    env = os.environ.copy()
    env['USE_SQLITE'] = 'True'
    env['USE_LOCMEM_CACHE'] = 'True'
    env['USE_INMEMORY_CHANNEL'] = 'True'
    
    CREATE_NO_WINDOW = 0x08000000
    
    try:
        django_process = subprocess.Popen(
            [sys.executable, manage_py, 'runserver', '127.0.0.1:8000', '--noreload'],
            cwd=app_dir,
            env=env,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start (check for up to 10 seconds)
        print("[*] Waiting for Django server to start...")
        import socket
        for i in range(20):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', 8000))
                sock.close()
                if result == 0:
                    print("[OK] Django server started successfully!")
                    return True
            except:
                pass
            time.sleep(0.5)
        
        print("[WARN] Django server may not have started properly")
        return True  # Continue anyway
        
    except Exception as e:
        print(f"[ERROR] Failed to start Django: {e}")
        return False


def start_print_dashboard():
    """Start Print Agent Dashboard in background"""
    global dashboard_process
    
    # Look for PrintAgentDashboard.exe in multiple locations
    if getattr(sys, 'frozen', False):
        # Running as exe - look in same folder as pos.exe (production deployment)
        exe_dir = os.path.dirname(sys.executable)
        dashboard_paths = [
            os.path.join(exe_dir, 'PrintAgentDashboard.exe'),  # Same folder as pos.exe
            os.path.join(os.path.dirname(exe_dir), 'PrintAgentDashboard.exe'),  # Parent folder
        ]
    else:
        # Running as script - look in development locations
        app_dir = get_app_dir()
        dashboard_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist', 'PrintAgentDashboard.exe'),  # print_agent/dist/
            os.path.join(app_dir, 'print_agent', 'dist', 'PrintAgentDashboard.exe'),  # From project root
            os.path.join(app_dir, 'PrintAgentDashboard.exe'),  # Root folder
        ]
    
    dashboard_exe = None
    for path in dashboard_paths:
        if os.path.exists(path):
            dashboard_exe = path
            break
    
    if not dashboard_exe:
        print("[WARN] PrintAgentDashboard.exe not found (skipping)")
        return False
    
    print(f"[*] Starting Print Dashboard from {os.path.basename(dashboard_exe)}...")
    
    CREATE_NO_WINDOW = 0x08000000
    
    try:
        dashboard_process = subprocess.Popen(
            [dashboard_exe],
            cwd=os.path.dirname(dashboard_exe),
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait a bit for dashboard to start
        time.sleep(1)
        
        # Check if still running
        if dashboard_process.poll() is None:
            print("[OK] Print Dashboard started successfully!")
            return True
        else:
            print("[WARN] Print Dashboard exited immediately")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to start Print Dashboard: {e}")
        return False


def cleanup():
    """Stop all background processes"""
    global django_process, dashboard_process
    
    print("\n[*] Shutting down services...")
    
    if django_process:
        try:
            django_process.terminate()
            django_process.wait(timeout=5)
            print("[OK] Django server stopped")
        except:
            django_process.kill()
            print("[OK] Django server killed")
    
    if dashboard_process:
        try:
            dashboard_process.terminate()
            dashboard_process.wait(timeout=5)
            print("[OK] Print Dashboard stopped")
        except:
            dashboard_process.kill()
            print("[OK] Print Dashboard killed")


def open_chrome_kiosk(url):
    """Open Chrome in kiosk mode (true fullscreen without browser UI)"""
    chrome_paths = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        os.path.expanduser(r'~\AppData\Local\Google\Chrome\Application\chrome.exe'),
    ]
    
    chrome_exe = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_exe = path
            break
    
    if chrome_exe:
        try:
            # Create dedicated kiosk profile directory
            if getattr(sys, 'frozen', False):
                # Running as exe - store profile next to exe
                kiosk_profile = os.path.join(os.path.dirname(sys.executable), 'kiosk-profile')
            else:
                # Running as script - store in project root
                kiosk_profile = os.path.join(get_app_dir(), 'kiosk-profile')
            
            # Launch Chrome in kiosk mode (fullscreen, no UI)
            # Using dedicated profile to separate from regular Chrome sessions
            subprocess.Popen([
                chrome_exe,
                '--kiosk',  # True fullscreen kiosk mode
                f'--user-data-dir={kiosk_profile}',  # Dedicated profile for kiosk
                '--no-first-run',
                '--disable-infobars',
                '--disable-session-crashed-bubble',
                '--disable-restore-session-state',
                '--disable-popup-blocking',
                url
            ])
            return True
        except Exception as e:
            print(f"[WARN] Failed to launch Chrome kiosk: {e}")
            return False
    return False


def create_window():
    """Create and configure the webview window"""
    
    # Try to detect available GUI backend
    # Priority: mshtml (works without pythonnet) > edgechrome (needs pythonnet)
    import platform
    import sys
    
    gui_backend = None
    if platform.system() == 'Windows':
        # Force mshtml backend which doesn't require pythonnet
        gui_backend = 'mshtml'
    
    # Create window with kiosk settings
    window = webview.create_window(
        title='YOGYA POS',
        url='http://127.0.0.1:8000/pos/',
        fullscreen=True,  # Start in fullscreen
        frameless=False,  # Keep frame for easier debugging (change to True for production kiosk)
        easy_drag=False,
        min_size=(1024, 768),
        background_color='#FFFFFF'
    )
    
    return window


def main():
    """Main launcher function"""
    print("=" * 60)
    print("YOGYA POS KIOSK LAUNCHER")
    print("=" * 60)
    
    # Check for single instance
    if not acquire_single_instance_lock():
        print("\n[INFO] POS is already running!")
        print("[INFO] Checking if Django server is accessible...")
        
        if is_django_running():
            print("[OK] Django server is running on http://127.0.0.1:8000")
            print("[INFO] Opening POS in new browser window...")
            print("[INFO] Press F11 in browser for fullscreen")
            
            # Open browser to existing instance
            webbrowser.open('http://127.0.0.1:8000/pos/?kiosk=1')
            return
        else:
            print("[WARN] Another instance detected but Django not responding")
            print("[WARN] Please close all pos.exe instances and try again")
            time.sleep(3)
            return
    
    # Register cleanup handler
    atexit.register(cleanup)
    
    # Check if Django already running (from previous instance)
    if is_django_running():
        print("\n[INFO] Django server already running - connecting to existing instance")
        django_ok = True
    else:
        # Start services
        django_ok = start_django_server()
    if not django_ok:
        print("\n[ERROR] Failed to start Django server. Exiting...")
        return
    
    # Start print dashboard (optional, don't fail if not found)
    start_print_dashboard()
    
    # Give services a moment to stabilize
    print("\n[*] Initializing services...")
    time.sleep(2)
    
    print("\n[*] Opening POS application...")
    print("=" * 60)
    if WEBVIEW_AVAILABLE:
        print("[INFO] Press F11 for fullscreen toggle")
        print("[INFO] Close window to exit application")
    else:
        print("[INFO] Opening in default browser")
        print("[INFO] Close browser tab when done")
    print("=" * 60)
    
    # Create and start webview window or browser
    global browser_opened
    try:
        if WEBVIEW_AVAILABLE:
            # Try pywebview with different backends
            try:
                window = create_window()
                webview.start(debug=False)
            except Exception as webview_error:
                print(f"[WARN] pywebview error: {webview_error}")
                print("[INFO] Falling back to Chrome kiosk mode...")
                if not browser_opened:
                    # Try Chrome kiosk mode first (true fullscreen)
                    if open_chrome_kiosk('http://127.0.0.1:8000/pos/'):
                        print("\n[OK] POS opened in Chrome kiosk mode (fullscreen)")
                    else:
                        # Fallback to default browser
                        print("[INFO] Chrome not found, using default browser...")
                        webbrowser.open('http://127.0.0.1:8000/pos/')
                        print("\n[OK] POS opened in browser")
                        print("[TIP] Press F11 for fullscreen")
                    browser_opened = True
                # Keep running until Ctrl+C
                print("Press Ctrl+C to stop services...")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
        else:
            # Use Chrome kiosk or default browser
            if not browser_opened:
                # Try Chrome kiosk mode first (true fullscreen)
                if open_chrome_kiosk('http://127.0.0.1:8000/pos/'):
                    print("\n[OK] POS opened in Chrome kiosk mode (fullscreen)")
                else:
                    # Fallback to default browser
                    print("[INFO] Chrome not found, using default browser...")
                    webbrowser.open('http://127.0.0.1:8000/pos/')
                    print("\n[OK] POS opened in browser")
                    print("[TIP] Press F11 for fullscreen")
                browser_opened = True
            print("Press Ctrl+C to stop services...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
                
    except KeyboardInterrupt:
        print("\n\n[WARN] Interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup will be called automatically via atexit
    print("\nThank you for using YOGYA POS!")


if __name__ == '__main__':
    main()
