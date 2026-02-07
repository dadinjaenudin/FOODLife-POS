"""
YOGYA POS Launcher - PyQt6 Edition
===================================
Cross-platform POS launcher with embedded Chromium engine.

Features:
- Dual display support (Main POS + Customer Display)
- Local API server for printing and display updates
- No external webview runtime required
- Cross-platform (Windows & Linux)
- Bundle-friendly (can be compiled to single executable)
"""
import os
import sys
import json
import time
import atexit
import requests
import subprocess
from pathlib import Path
from threading import Thread

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView

# Global process trackers
api_server_process = None


def get_launcher_dir():
    """Get launcher directory"""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return Path(os.path.dirname(sys.executable))
    else:
        # Running as script
        return Path(os.path.dirname(os.path.abspath(__file__)))


def load_config():
    """Load terminal configuration from config.json"""
    launcher_dir = get_launcher_dir()
    config_paths = [
        launcher_dir / 'config.json',
        launcher_dir.parent / 'config.json',
        Path.cwd() / 'config.json',
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"[Config] Loaded: {config_path}")
                    return config
            except Exception as e:
                print(f"[Config] Error reading {config_path}: {e}")
    
    print("[Config] No config.json found")
    return {}


def validate_terminal(config):
    """Validate terminal with Edge Server"""
    if not config or 'terminal_code' not in config:
        return None
    
    edge_server = config.get('edge_server', 'http://127.0.0.1:8001')
    terminal_code = config.get('terminal_code')
    
    print(f"[Terminal] Validating {terminal_code}...")
    
    try:
        response = requests.post(
            f"{edge_server}/api/terminal/validate",
            json={
                'terminal_code': terminal_code,
                'company_code': config.get('company_code'),
                'brand_code': config.get('brand_code'),
                'store_code': config.get('store_code')
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"[Terminal] Validated: {terminal_code}")
                return data
        
        print(f"[Terminal] Validation failed")
        return None
    except Exception as e:
        print(f"[Terminal] Validation error: {e}")
        return None


def start_local_api_server():
    """Start Flask API server in background"""
    global api_server_process
    
    launcher_dir = get_launcher_dir()
    api_script = launcher_dir / 'local_api.py'
    
    if not api_script.exists():
        print("[API Server] local_api.py not found")
        return False
    
    print("[API Server] Starting...")
    
    try:
        # Start Flask server as subprocess
        api_server_process = subprocess.Popen(
            [sys.executable, str(api_script)],
            cwd=str(launcher_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        # Wait for server to be ready (check multiple times)
        print("[API Server] Waiting for startup...")
        for i in range(10):
            time.sleep(1)
            try:
                response = requests.get('http://127.0.0.1:5000/health', timeout=1)
                if response.status_code == 200:
                    print(f"[API Server] Started successfully on http://127.0.0.1:5000")
                    return True
            except:
                print(f"[API Server] Attempt {i+1}/10...")
        
        print("[API Server] Failed to start after 10 seconds")
        
        # Check if process is still running
        if api_server_process.poll() is not None:
            # Process died, get error output
            stderr = api_server_process.stderr.read().decode('utf-8', errors='ignore')
            print(f"[API Server] Error output: {stderr[:500]}")
        
        return False
    except Exception as e:
        print(f"[API Server] Error: {e}")
        return False


def cleanup():
    """Clean up resources on exit"""
    global api_server_process
    
    print("\n[Launcher] Shutting down...")
    
    if api_server_process:
        try:
            api_server_process.terminate()
            api_server_process.wait(timeout=5)
            print("[API Server] Stopped")
        except:
            api_server_process.kill()
            print("[API Server] Killed")


class POSWindow(QWebEngineView):
    """Main POS window"""
    
    def __init__(self, url, customer_window=None):
        super().__init__()
        self.setWindowTitle('YOGYA POS')
        self.customer_window = customer_window
        
        print(f"[POSWindow] Loading URL: {url}", flush=True)
        
        # Use default profile - DO NOT clear cache or modify it
        # (Customer display uses separate profile to avoid conflicts)
        profile = QWebEngineProfile.defaultProfile()
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        
        # Clear session cookies to force fresh login (for security)
        cookie_store = profile.cookieStore()
        cookie_store.deleteAllCookies()
        print("[POSWindow] Session cookies cleared - fresh login required")
        
        print("[POSWindow] Using default profile with persistent cookies (no cache clearing)")
        
        # Enable features
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        
        # Add console message handler to debug issues
        page = self.page()
        page.javaScriptConsoleMessage = self._handle_console_message
        
        # Connect error and progress signals for debugging
        self.loadStarted.connect(self._on_load_started)
        self.loadProgress.connect(self._on_load_progress)
        self.loadFinished.connect(self._on_load_finished)
        
        # Load URL
        self.load(QUrl(url))
        print(f"[POSWindow] QUrl created from: {QUrl(url).toString()}", flush=True)
        
        # Development mode: Windowed (comment out for production fullscreen)
        self.resize(1366, 768)
        self.show()
        # Production mode: Fullscreen (uncomment for production)
        # self.showFullScreen()
    
    def _on_load_started(self):
        """Called when page load starts"""
        print("[POSWindow] Loading started...", flush=True)
    
    def _on_load_progress(self, progress):
        """Called during page load progress"""
        if progress % 25 == 0:  # Log every 25%
            print(f"[POSWindow] Loading progress: {progress}%", flush=True)
    
    def _on_load_finished(self, success):
        """Called when page load finishes (success or failure)"""
        if success:
            print("[POSWindow] ✅ Page loaded successfully", flush=True)
            
            # Inject kiosk mode flag into localStorage
            self.page().runJavaScript("""
                localStorage.setItem('kiosk_mode', '1');
                console.log('✅ Kiosk mode set via localStorage');
            """)
        else:
            print("[POSWindow] ❌ Page failed to load!", flush=True)
            
            # Get current URL to see if redirect happened
            current_url = self.url().toString()
            print(f"[POSWindow] Current URL: {current_url}", flush=True)
            
            # Get page HTML to see what's loaded
            self.page().toHtml(self._print_page_html)
    
    def _print_page_html(self, html):
        """Print first 500 chars of page HTML for debugging"""
        preview = html[:500] if len(html) > 500 else html
        print(f"[POSWindow] Page HTML preview: {preview}...", flush=True)
    
    def _handle_console_message(self, level, message, lineNumber, sourceID):
        """Handle JavaScript console messages for debugging"""
        level_names = {0: "INFO", 1: "WARNING", 2: "ERROR"}
        level_name = level_names.get(level, "UNKNOWN")
        print(f"[POS Console] [{level_name}] {message} (line {lineNumber})", flush=True)
    
    def closeEvent(self, event):
        """Close customer window when main window closes"""
        if self.customer_window:
            self.customer_window.close()
        event.accept()


class CustomerDisplayPage(QWebEnginePage):
    """Custom page to capture console messages from customer display"""
    
    def __init__(self, profile, parent=None):
        """Initialize page with custom profile"""
        super().__init__(profile, parent)
    
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """Capture and log JavaScript console messages"""
        level_names = {
            0: "INFO",
            1: "WARNING",
            2: "ERROR"
        }
        level_name = level_names.get(level, "UNKNOWN")
        
        # Handle Unicode by encoding and decoding safely
        try:
            safe_message = message.encode('ascii', 'replace').decode('ascii')
            print(f"[Customer Display Console] [{level_name}] {safe_message} (line {lineNumber})")
        except:
            print(f"[Customer Display Console] [{level_name}] <message contains special characters> (line {lineNumber})")


class CustomerDisplayWindow(QWebEngineView):
    """Customer display window (for secondary monitor)"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Customer Display')
        
        # Create SEPARATE in-memory profile for customer display
        # Store as instance variable to prevent premature deletion
        self.profile = QWebEngineProfile("customer_display", self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        print("[Customer Display] Using separate in-memory profile (no cache conflicts)")
        
        # Set custom page with separate profile to capture console messages
        custom_page = CustomerDisplayPage(self.profile, self)
        self.setPage(custom_page)
        
        # Enable ALL necessary features for JavaScript execution
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowGeolocationOnInsecureOrigins, True)
        
        # Enable console message output for debugging
        print("[Customer Display] JavaScript enabled with full permissions")
        
        # Load customer display from local API server (not local file to avoid CORS issues)
        self.load(QUrl('http://127.0.0.1:5000/'))
        
        # Move to secondary monitor if available
        screens = QApplication.screens()
        if len(screens) > 1:
            # Place on second monitor
            geometry = screens[1].geometry()
            self.move(geometry.left(), geometry.top())
            # Development mode: Windowed (comment out for production fullscreen)
            self.resize(1024, 768)
            self.show()
            # Production mode: Fullscreen (uncomment for production)
            # self.resize(geometry.width(), geometry.height())
            # self.showFullScreen()
        else:
            # No second monitor, show as window
            self.resize(800, 600)
            self.show()


def main():
    """Main launcher function"""
    print("=" * 60)
    print("YOGYA POS LAUNCHER - PyQt6 Edition")
    print("=" * 60)
    
    # Enable remote debugging for WebEngine (MUST be set BEFORE QApplication)
    # Access DevTools at: http://localhost:9222
    os.environ['QTWEBENGINE_REMOTE_DEBUGGING'] = '9222'
    print("[Debug] Remote debugging enabled on port 9222")
    print("[Debug] Access DevTools: http://localhost:9222")
    
    # Create QApplication FIRST (required before any Qt widgets)
    app = QApplication(sys.argv)
    app.setApplicationName("YOGYA POS Launcher")
    
    # Register cleanup
    atexit.register(cleanup)
    
    # Load configuration
    config = load_config()
    
    # Check if customer display is enabled
    enable_customer_display = config.get('enable_customer_display', False)
    
    # Start local API server (REQUIRED for customer display)
    if enable_customer_display:
        print("\n[*] Starting Local API Server...")
        if not start_local_api_server():
            print("[ERROR] API server failed to start!")
            print("[ERROR] Customer display and print features will not work")
            print("[ERROR] Check if port 5000 is already in use")
            
            # Wait for user acknowledgment
            input("\nPress Enter to continue anyway (or Ctrl+C to cancel)...")
    else:
        print("\n[INFO] Local API Server: SKIPPED (customer display disabled)")
    
    # Validate terminal
    validation = validate_terminal(config)
    
    # Get POS URL with kiosk mode parameter
    if validation and validation.get('success'):
        edge_server = config.get('edge_server', 'http://127.0.0.1:8001')
        redirect_url = validation.get('redirect_url')
        pos_url = f"{edge_server}{redirect_url}"
    else:
        # Fallback to default
        pos_url = config.get('edge_server', 'http://127.0.0.1:8001') + '/pos/'
    
    # Add kiosk mode parameter for local API integration
    print(f"[DEBUG] pos_url BEFORE kiosk: {pos_url}", flush=True)
    separator = '&' if '?' in pos_url else '?'
    pos_url = f"{pos_url}{separator}kiosk=1"
    
    print(f"[POS] URL WITH KIOSK: {pos_url}", flush=True)
    print(f"[DEBUG] separator used: '{separator}'", flush=True)
    
    # Write URL to debug file
    with open('url_debug.txt', 'w') as f:
        f.write(f"pos_url before kiosk: {pos_url.replace(f'{separator}kiosk=1', '')}\n")
        f.write(f"separator: {separator}\n")
        f.write(f"final pos_url: {pos_url}\n")
    
    # Create customer display window if enabled
    customer_window = None
    if enable_customer_display:
        print("[INFO] Customer display: ENABLED")
        customer_window = CustomerDisplayWindow()
    else:
        print("[INFO] Customer display: DISABLED (config.enable_customer_display = false)")
    
    # Create main POS window (with reference to customer window)
    pos_window = POSWindow(pos_url, customer_window)
    
    print("=" * 60)
    print("[INFO] POS Launcher running")
    print("[INFO] Main POS: Fullscreen on primary monitor")
    if enable_customer_display:
        print("[INFO] Customer Display: Fullscreen on secondary monitor (if available)")
        print("[INFO] Local API: http://127.0.0.1:5000")
    print("[INFO] Press Alt+F4 to exit")
    print("=" * 60)
    
    # Run application
    exit_code = app.exec()
    
    print("\nThank you for using YOGYA POS!")
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
