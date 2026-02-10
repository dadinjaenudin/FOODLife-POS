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

from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QFont, QIcon
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
    """
    Validate terminal with Edge Server
    
    Returns:
        tuple: (success: bool, error_type: str, data: dict, error_message: str)
    """
    if not config or 'terminal_code' not in config:
        return (False, "config_missing", None, 
                "Configuration file (config.json) is missing or invalid.\nPlease check terminal_code, store_code, company_code.")
    
    edge_server = config.get('edge_server', 'http://127.0.0.1:8001')
    terminal_code = config.get('terminal_code')
    store_code = config.get('store_code')
    company_code = config.get('company_code')
    
    # Check required fields
    if not store_code or not company_code:
        return (False, "config_missing", None,
                f"Required configuration fields are missing.\n\n"
                f"Please update config.json with terminal_code, store_code, and company_code.")
    
    print(f"[Terminal] Validating {terminal_code} @ {store_code} ({company_code})...")
    
    try:
        response = requests.post(
            f"{edge_server}/api/terminal/validate",
            json={
                'terminal_code': terminal_code,
                'company_code': company_code,
                'brand_code': config.get('brand_code'),
                'store_code': store_code
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('valid'):
                print(f"[Terminal] ✓ Validated: {terminal_code}")
                return (True, None, data, None)
            else:
                error = data.get('error', 'Unknown error')
                return (False, "validation_error", None, f"Terminal validation failed:\n\n{error}")
        elif response.status_code == 404:
            error_data = response.json()
            error_msg = error_data.get('error', 'Terminal not found')
            return (False, "not_found", None,
                    f"The terminal configuration does not match any registered terminal.\n\n{error_msg}")
        else:
            return (False, "validation_error", None, 
                    f"Server returned error {response.status_code}:\n{response.text}")
        
    except requests.exceptions.ConnectionError:
        return (False, "connection_error", None,
                f"Cannot connect to Edge Server at {edge_server}\n\n"
                f"The server may be offline or unreachable.")
    except requests.exceptions.Timeout:
        return (False, "connection_error", None,
                f"Connection timeout to Edge Server at {edge_server}\n\n"
                f"The server is not responding.")
    except Exception as e:
        return (False, "validation_error", None, f"Validation error:\n{str(e)}")


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
    
    # Validate required fields (same as API requirement)
    if not store_code or not company_code:
        print(f"[Config] Cannot fetch device config: store_code and company_code are required")
        return None
    
    print(f"[Config] Fetching device config from API for {terminal_code}...")
    
    try:
        # Build query params with all identifiers (REQUIRED for security)
        params = {
            'terminal_code': terminal_code,
            'company_code': company_code,
            'store_code': store_code
        }
        if brand_code:
            params['brand_code'] = brand_code
        
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


class ValidationErrorDialog(QDialog):
    """Custom styled error dialog for terminal validation failures"""
    
    def __init__(self, error_type, error_message, config=None):
        super().__init__()
        self.setWindowTitle("YOGYA POS - Terminal Validation")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # ========== HEADER ==========
        header_layout = QHBoxLayout()
        
        # Error icon (large red X)
        icon_label = QLabel("⚠️")
        icon_font = QFont()
        icon_font.setPointSize(48)
        icon_label.setFont(icon_font)
        icon_label.setStyleSheet("color: #DC2626;")
        header_layout.addWidget(icon_label)
        
        # Title and subtitle
        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)
        
        title_label = QLabel("Terminal Validation Failed")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #1F2937;")
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Cannot start POS application")
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: #6B7280;")
        title_layout.addWidget(subtitle_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Separator line
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #E5E7EB;")
        layout.addWidget(separator)
        
        # ========== ERROR MESSAGE ==========
        error_box = QTextEdit()
        error_box.setReadOnly(True)
        error_box.setMinimumHeight(200)
        
        # Format error message with HTML
        html_content = self._format_error_html(error_type, error_message, config)
        error_box.setHtml(html_content)
        
        # Style the text box
        error_box.setStyleSheet("""
            QTextEdit {
                background-color: #FEF2F2;
                border: 2px solid #FCA5A5;
                border-radius: 8px;
                padding: 15px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
            }
        """)
        layout.addWidget(error_box)
        
        # ========== SUGGESTIONS ==========
        suggestions = self._get_suggestions(error_type)
        if suggestions:
            suggestion_label = QLabel("💡 <b>What to do:</b>")
            suggestion_label.setStyleSheet("color: #1F2937; font-size: 11pt;")
            layout.addWidget(suggestion_label)
            
            suggestion_text = QLabel(suggestions)
            suggestion_text.setWordWrap(True)
            suggestion_text.setStyleSheet("""
                color: #374151;
                font-size: 10pt;
                background-color: #F3F4F6;
                padding: 12px;
                border-radius: 6px;
                border-left: 4px solid #3B82F6;
            """)
            layout.addWidget(suggestion_text)
        
        # ========== BUTTONS ==========
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("Close Application")
        close_button.setMinimumWidth(150)
        close_button.setMinimumHeight(40)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
            QPushButton:pressed {
                background-color: #991B1B;
            }
        """)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Window styling
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
        """)
    
    def _format_error_html(self, error_type, error_message, config):
        """Format error message as HTML"""
        html = "<div style='font-family: Segoe UI, Arial; color: #991B1B;'>"
        
        # Error type heading
        if error_type == "not_found":
            html += "<h3 style='color: #DC2626; margin-top: 0;'>❌ Terminal Not Found</h3>"
        elif error_type == "config_missing":
            html += "<h3 style='color: #DC2626; margin-top: 0;'>📋 Configuration Missing</h3>"
        elif error_type == "connection_error":
            html += "<h3 style='color: #DC2626; margin-top: 0;'>🔌 Connection Error</h3>"
        else:
            html += "<h3 style='color: #DC2626; margin-top: 0;'>⚠️ Validation Error</h3>"
        
        # Error message
        html += f"<p style='color: #7F1D1D; font-size: 11pt; line-height: 1.6;'>{error_message.replace(chr(10), '<br>')}</p>"
        
        # Config values if provided
        if config:
            html += "<hr style='border: none; border-top: 1px solid #FCA5A5; margin: 15px 0;'>"
            html += "<p style='color: #6B7280; font-size: 10pt; margin-bottom: 8px;'><b>Configuration Values:</b></p>"
            html += "<table style='width: 100%; border-collapse: collapse; font-size: 10pt;'>"
            
            fields = [
                ('terminal_code', 'Terminal Code'),
                ('store_code', 'Store Code'),
                ('company_code', 'Company Code'),
                ('brand_code', 'Brand Code'),
                ('edge_server', 'Edge Server')
            ]
            
            for key, label in fields:
                value = config.get(key, '<span style="color: #DC2626;">MISSING</span>')
                if value and key != 'edge_server':
                    value = f"<b>{value}</b>"
                html += f"""
                <tr>
                    <td style='padding: 4px; color: #6B7280; width: 40%;'>{label}:</td>
                    <td style='padding: 4px; color: #1F2937;'>{value}</td>
                </tr>
                """
            
            html += "</table>"
        
        html += "</div>"
        return html
    
    def _get_suggestions(self, error_type):
        """Get helpful suggestions based on error type"""
        if error_type == "not_found":
            return ("• Check that terminal_code matches your registered terminal<br>"
                    "• Verify store_code matches the store where this terminal belongs<br>"
                    "• Contact IT support to register this terminal if it's new")
        
        elif error_type == "config_missing":
            return ("• Open <b>config.json</b> file in the launcher directory<br>"
                    "• Add missing fields: terminal_code, store_code, company_code<br>"
                    "• Save the file and restart the application")
        
        elif error_type == "connection_error":
            return ("• Check that Edge Server is running (docker-compose up)<br>"
                    "• Verify network connection and firewall settings<br>"
                    "• Contact IT support if problem persists")
        
        else:
            return "• Review your config.json file<br>• Contact IT support for assistance"


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
        
        # Fullscreen mode
        self.showFullScreen()
        print("[POSWindow] Running in FULLSCREEN mode")
    
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
    
    def keyPressEvent(self, event):
        """Handle keyboard events - Press ESC to exit fullscreen"""
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                print("[POSWindow] ESC pressed - Exiting fullscreen mode")
                self.showNormal()
                self.resize(1366, 768)
            else:
                print("[POSWindow] ESC pressed - Entering fullscreen mode")
                self.showFullScreen()
        else:
            super().keyPressEvent(event)
    
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
            # Place on second monitor FULLSCREEN
            print(f"[Customer Display] Detected {len(screens)} monitors")
            geometry = screens[1].geometry()
            print(f"[Customer Display] Monitor 2 geometry: {geometry.width()}x{geometry.height()} at ({geometry.left()}, {geometry.top()})")
            self.setGeometry(geometry)
            self.showFullScreen()
            print("[Customer Display] Running in FULLSCREEN mode on secondary monitor")
        else:
            # No second monitor - show fullscreen on primary
            print("[Customer Display] Only 1 monitor detected - using primary monitor")
            self.showFullScreen()
            print("[Customer Display] Running in FULLSCREEN mode on primary monitor")
    
    def keyPressEvent(self, event):
        """Handle keyboard events - Press ESC to exit fullscreen"""
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                print("[Customer Display] ESC pressed - Exiting fullscreen mode")
                self.showNormal()
                self.resize(1024, 768)
            else:
                print("[Customer Display] ESC pressed - Entering fullscreen mode")
                self.showFullScreen()
        else:
            super().keyPressEvent(event)


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
    
    # ========================================
    # VALIDATE TERMINAL CONFIGURATION (MANDATORY)
    # ========================================
    print("\n[*] Validating Terminal Configuration...")
    success, error_type, validation_data, error_message = validate_terminal(config)
    
    if not success:
        # Show custom error dialog and EXIT
        print(f"[ERROR] Terminal validation failed!")
        print(f"[ERROR] Type: {error_type}")
        print(f"[ERROR] {error_message}")
        
        # Create and show custom styled error dialog
        error_dialog = ValidationErrorDialog(error_type, error_message, config)
        error_dialog.exec()
        
        print("[EXIT] Application terminated due to invalid configuration")
        sys.exit(1)
    
    print(f"[Terminal] ✓ Configuration validated successfully")
    
    # Get POS URL with kiosk mode parameter
    edge_server = config.get('edge_server', 'http://127.0.0.1:8001')
    redirect_url = validation_data.get('redirect_url')
    if redirect_url:
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
