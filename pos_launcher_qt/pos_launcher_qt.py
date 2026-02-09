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
api_server_thread = None
flask_app = None
cleanup_done = False  # Flag to prevent cleanup from running multiple times


def get_launcher_dir():
    """Get launcher directory"""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        # PyInstaller puts data files in _internal subdirectory
        exe_dir = Path(os.path.dirname(sys.executable))
        internal_dir = exe_dir / '_internal'
        if internal_dir.exists():
            return internal_dir
        return exe_dir
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
            if data.get('valid'):
                print(f"[Terminal] Validated: {terminal_code}")
                return data
        
        print(f"[Terminal] Validation failed")
        return None
    except Exception as e:
        print(f"[Terminal] Validation error: {e}")
        return None


def fetch_terminal_config_from_api(config):
    """
    Fetch terminal device configuration from Edge Server API.
    
    This retrieves all device settings (customer display, printer config, kitchen config, etc.)
    from the centralized database, eliminating the need for manual JSON configuration.
    
    Args:
        config (dict): Local config containing terminal_code and edge_server
        
    Returns:
        dict: Device configuration from API, or None if API unavailable
    """
    if not config or 'terminal_code' not in config:
        return None
    
    edge_server = config.get('edge_server', 'http://127.0.0.1:8001')
    terminal_code = config.get('terminal_code')
    company_code = config.get('company_code')
    brand_code = config.get('brand_code')
    store_code = config.get('store_code')
    
    print(f"[Config] Fetching device config from API for {terminal_code}...")
    
    try:
        # Build query params with all identifiers
        params = {'terminal_code': terminal_code}
        if company_code:
            params['company_code'] = company_code
        if brand_code:
            params['brand_code'] = brand_code
        if store_code:
            params['store_code'] = store_code
        
        response = requests.get(
            f"{edge_server}/api/terminal/config",
            params=params,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                device_config = data.get('terminal', {}).get('device_config', {})
                print(f"[Config] Device config loaded from API")
                print(f"[Config]   - Customer Display: {device_config.get('enable_customer_display', False)}")
                print(f"[Config]   - Printer Type: {device_config.get('printer_type', 'N/A')}")
                print(f"[Config]   - Kitchen Printer: {device_config.get('enable_kitchen_printer', False)}")
                
                # Payment Configuration
                payment_methods = device_config.get('default_payment_methods', [])
                edc_mode = device_config.get('edc_integration_mode', 'manual')
                if payment_methods:
                    print(f"[Config]   - Payment Methods: {', '.join(payment_methods)}")
                    print(f"[Config]   - EDC Mode: {edc_mode}")
                
                return device_config
        
        print(f"[Config] API returned status {response.status_code}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[Config] API fetch failed: {e}")
        return None
    except Exception as e:
        print(f"[Config] Unexpected error: {e}")
        return None


def kill_process_on_port(port=5000):
    """Kill any process using the specified port"""
    import platform
    
    try:
        if platform.system() == 'Windows':
            # Windows: Use netstat to find PID using the port
            print(f"[Port Check] Checking if port {port} is in use...")
            result = subprocess.run(
                ['netstat', '-ano', '-p', 'TCP'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            for line in result.stdout.splitlines():
                if f':{port}' in line and 'LISTENING' in line:
                    # Extract PID (last column)
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        print(f"[Port Check] Port {port} is in use by PID {pid}")
                        
                        # Kill the process
                        try:
                            subprocess.run(
                                ['taskkill', '/F', '/PID', pid],
                                capture_output=True,
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                            )
                            print(f"[Port Check] Killed process {pid}")
                            time.sleep(1)  # Wait for port to be released
                            return True
                        except Exception as e:
                            print(f"[Port Check] Failed to kill process {pid}: {e}")
                            return False
            
            print(f"[Port Check] Port {port} is free")
            return True
            
        else:
            # Linux: Use lsof to find and kill process
            print(f"[Port Check] Checking if port {port} is in use...")
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                pid = result.stdout.strip()
                print(f"[Port Check] Port {port} is in use by PID {pid}")
                
                # Kill the process
                try:
                    subprocess.run(['kill', '-9', pid], check=True)
                    print(f"[Port Check] Killed process {pid}")
                    time.sleep(1)  # Wait for port to be released
                    return True
                except Exception as e:
                    print(f"[Port Check] Failed to kill process {pid}: {e}")
                    return False
            
            print(f"[Port Check] Port {port} is free")
            return True
            
    except Exception as e:
        print(f"[Port Check] Error checking port: {e}")
        return True  # Continue anyway


def start_local_api_server():
    """Start Flask API server in background thread"""
    global api_server_thread, flask_app
    
    # Kill any existing process on port 5000
    kill_process_on_port(5000)
    
    launcher_dir = get_launcher_dir()
    
    print("[API Server] Starting Flask server as background thread...")
    
    try:
        # Import Flask app from local_api module
        # Add launcher_dir to sys.path so we can import local_api
        if str(launcher_dir) not in sys.path:
            sys.path.insert(0, str(launcher_dir))
        
        # Import the Flask app and run function from local_api
        try:
            from local_api import app as flask_app, run_server
            print("[API Server] Flask app imported successfully")
        except ImportError as e:
            print(f"[API Server] Failed to import local_api: {e}")
            return False
        
        # Start Flask server in daemon thread (will shut down when main app exits)
        def run_flask():
            try:
                print("[API Server] Flask thread starting...")
                run_server()  # This is the Flask app.run() wrapper
            except Exception as e:
                print(f"[API Server] Flask thread error: {e}")
        
        api_server_thread = Thread(target=run_flask, daemon=True)
        api_server_thread.start()
        
        # Wait for server to be ready (check multiple times)
        print("[API Server] Waiting for startup...")
        for i in range(15):  # Increased to 15 attempts
            time.sleep(1)
            try:
                response = requests.get('http://127.0.0.1:5000/health', timeout=1)
                if response.status_code == 200:
                    print(f"[API Server] Health check passed")
                    
                    # Extra verification: Check customer-display endpoint
                    print("[API Server] Verifying customer-display HTML endpoint...")
                    time.sleep(1)  # Brief delay
                    try:
                        cd_response = requests.get('http://127.0.0.1:5000/customer-display', timeout=2)
                        if cd_response.status_code == 200:
                            print("[API Server] ✓ Customer display HTML endpoint ready")
                            
                            # CRITICAL: Also test the config API endpoint that JavaScript will fetch
                            print("[API Server] Verifying customer-display config API endpoint...")
                            time.sleep(1)
                            try:
                                config_response = requests.get('http://127.0.0.1:5000/api/customer-display/config', timeout=2)
                                if config_response.status_code == 200:
                                    print("[API Server] ✓ Customer display config API endpoint ready")
                                    print(f"[API Server] ✓ All endpoints verified - server is FULLY ready")
                                    return True
                                else:
                                    print(f"[API Server] Config API returned {config_response.status_code}, retrying...")
                            except Exception as e:
                                print(f"[API Server] Config API not ready yet: {e}")
                                continue
                        else:
                            print(f"[API Server] Customer display HTML returned {cd_response.status_code}, retrying...")
                    except Exception as e:
                        print(f"[API Server] Customer display HTML not ready yet: {e}")
                        continue
            except:
                print(f"[API Server] Attempt {i+1}/15...")
        
        print("[API Server] Failed to start after 15 seconds")
        return False
        
    except Exception as e:
        print(f"[API Server] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup():
    """Clean up resources on exit"""
    global api_server_thread, cleanup_done
    
    # Prevent cleanup from running multiple times
    if cleanup_done:
        return
    
    cleanup_done = True
    print("\n[Launcher] Shutting down...")
    
    # Flask server thread is daemon, so it will automatically shut down with main process
    if api_server_thread and api_server_thread.is_alive():
        print("[API Server] Flask server will shut down with main process (daemon thread)")
    
    # Ensure port 5000 is released
    print("[Cleanup] Releasing port 5000...")
    kill_process_on_port(5000)
    
    print("[Launcher] Goodbye!")


class POSWindow(QWebEngineView):
    """Main POS window"""
    
    def __init__(self, url, customer_window=None, config=None):
        super().__init__()
        self.setWindowTitle('YOGYA POS')
        self.customer_window = customer_window
        self.config = config
        
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
            
            # Inject kiosk mode flag and terminal/company/brand/store codes into localStorage
            terminal_code = self.config.get('terminal_code', '') if self.config else ''
            company_code = self.config.get('company_code', '') if self.config else ''
            brand_code = self.config.get('brand_code', '') if self.config else ''
            store_code = self.config.get('store_code', '') if self.config else ''
            
            js_code = f"""
                localStorage.setItem('kiosk_mode', '1');
                localStorage.setItem('terminal_code', '{terminal_code}');
                localStorage.setItem('company_code', '{company_code}');
                localStorage.setItem('brand_code', '{brand_code}');
                localStorage.setItem('store_code', '{store_code}');
                console.log('✅ Kiosk mode set via localStorage');
                console.log('✅ Terminal code set:', '{terminal_code}');
                console.log('✅ Company code set:', '{company_code}');
                console.log('✅ Brand code set:', '{brand_code}');
                console.log('✅ Store code set:', '{store_code}');
            """
            self.page().runJavaScript(js_code)
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
        """Close customer window and cleanup resources when main window closes"""
        print("[POSWindow] Close event triggered - cleaning up...")
        
        # Close customer display window
        if self.customer_window:
            self.customer_window.close()
        
        # Run cleanup to release port 5000 and stop Flask server
        cleanup()
        
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
        self.api_url = 'http://127.0.0.1:5000/customer-display'
        
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
        
        # DO NOT load URL here - will be loaded after API server is confirmed ready
        print("[Customer Display] Window initialized, waiting for API server...")
    
    def load_display(self):
        """Load customer display URL after API server is ready"""
        print(f"[Customer Display] Loading: {self.api_url}")
        self.load(QUrl(self.api_url))
        
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
    
    # Fetch device configuration from API (centralized settings management)
    device_config = fetch_terminal_config_from_api(config)
    
    if device_config:
        # API available - use centralized configuration
        print("[Config] Using device configuration from API (centralized management)")
        config['device_config'] = device_config
    else:
        # API unavailable - disable customer display (requires API)
        print("[Config] API unavailable, customer display will be disabled")
        config['device_config'] = {
            'enable_customer_display': False,  # Customer display requires API connection
            # Other device settings would come from API
        }
    
    # Check if customer display is enabled (from API only)
    enable_customer_display = config['device_config'].get('enable_customer_display', False)
    
    # Start local API server (REQUIRED for customer display)
    api_server_ready = False
    if enable_customer_display:
        print("\n[*] Starting Local API Server...")
        api_server_ready = start_local_api_server()
        if not api_server_ready:
            print("[WARNING] API server failed to start!")
            print("[WARNING] Customer display and print features may not work")
            print("[WARNING] Continuing without customer display...")
            time.sleep(2)  # Brief pause to show warning
            enable_customer_display = False  # Disable customer display if API fails
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
    
    # Add terminal code and kiosk mode parameters
    terminal_code = config.get('terminal_code')
    print(f"[DEBUG] pos_url BEFORE params: {pos_url}", flush=True)
    separator = '&' if '?' in pos_url else '?'
    
    # Add terminal parameter first, then kiosk
    if terminal_code:
        pos_url = f"{pos_url}{separator}terminal={terminal_code}"
        separator = '&'  # Next parameter uses & separator
        print(f"[POS] Terminal parameter added: {terminal_code}")
    
    pos_url = f"{pos_url}{separator}kiosk=1"
    
    print(f"[POS] Final URL: {pos_url}", flush=True)
    print(f"[DEBUG] Parameters: terminal={terminal_code}, kiosk=1", flush=True)
    
    # Write URL to debug file
    with open('url_debug.txt', 'w') as f:
        f.write(f"pos_url before kiosk: {pos_url.replace(f'{separator}kiosk=1', '')}\n")
        f.write(f"separator: {separator}\n")
        f.write(f"final pos_url: {pos_url}\n")
    
    # Create customer display window if enabled AND API server is ready
    customer_window = None
    if enable_customer_display and api_server_ready:
        print("[INFO] Customer display: ENABLED")
        customer_window = CustomerDisplayWindow()
        
        # Give extra time for API server to fully stabilize
        print("[Customer Display] Waiting 3 seconds for API server to stabilize...")
        time.sleep(3)
        
        # Final verification: Test the config endpoint one more time before loading
        print("[Customer Display] Final verification of config endpoint...")
        try:
            test_response = requests.get('http://127.0.0.1:5000/api/customer-display/config', timeout=2)
            if test_response.status_code == 200:
                print("[Customer Display] ✓ Config endpoint confirmed working")
                print(f"[Customer Display] Config data length: {len(test_response.content)} bytes")
            else:
                print(f"[Customer Display] ⚠️ Config endpoint returned status {test_response.status_code}")
        except Exception as e:
            print(f"[Customer Display] ⚠️ Config endpoint test failed: {e}")
        
        # Load display URL after window is created and API is ready
        customer_window.load_display()
    else:
        if enable_customer_display and not api_server_ready:
            print("[INFO] Customer display: DISABLED (API server not ready)")
        else:
            print("[INFO] Customer display: DISABLED (config.enable_customer_display = false)")
    
    # Create main POS window (with reference to customer window and config)
    pos_window = POSWindow(pos_url, customer_window, config)
    
    print("=" * 60)
    print("[INFO] POS Launcher running")
    print("[INFO] Main POS: Fullscreen on primary monitor")
    if enable_customer_display:
        print("[INFO] Customer Display: Fullscreen on secondary monitor (if available)")
        print("[INFO] API Dashboard: http://127.0.0.1:5000")
        print("[INFO] Customer Display: http://127.0.0.1:5000/customer-display")
    print("[INFO] Press Alt+F4 to exit")
    print("=" * 60)
    
    # Run application
    exit_code = app.exec()
    
    print("\nThank you for using YOGYA POS!")
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
