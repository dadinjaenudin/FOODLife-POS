"""
Local API Server for POS Launcher
==================================
Flask server running on localhost:5000

Endpoints:
- GET / - Serve customer display HTML
- POST /api/print - Print to local printer
- POST /api/customer-display/update - Update customer display data
- GET /api/customer-display/config - Get display configuration
- GET /api/customer-display/stream - SSE stream for real-time updates
- GET /health - Health check
"""
import json
import time
import queue
import platform
import os
import io
import base64
from pathlib import Path
from threading import Lock
from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    print("[Warning] qrcode library not installed. QR code generation disabled.")
    print("[Warning] Install with: pip install qrcode[pil]")

app = Flask(__name__)
CORS(app)  # Allow requests from webview

# 404 handler - Don't spam logs for browser requests like favicon
@app.errorhandler(404)
def handle_404(e):
    """Handle 404 errors silently for common browser requests"""
    # Don't print traceback for common browser requests
    if request.path not in ['/favicon.ico', '/robots.txt', '/apple-touch-icon.png']:
        print(f"[WARNING] 404 Not Found: {request.path}")
    return jsonify({
        'success': False,
        'error': 'Not Found',
        'path': request.path
    }), 404

# Global error handler - Always return JSON, never HTML
@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all exceptions and return JSON instead of HTML error pages"""
    print(f"[ERROR] Unhandled exception: {e}")
    import traceback
    traceback.print_exc()
    return jsonify({
        'success': False,
        'error': str(e),
        'type': type(e).__name__
    }), 500

# Customer display state
display_data = {
    'total': 0,
    'items': [],
    'customer_name': '',
    'show_qr': False,
    'qr_code': None,
    'payment_method': None,
    'bill_panel_html': None,
    'has_bill': False,
    'show_modal': False,
    'modal_html': None,
    'updated_at': time.time()
}
display_lock = Lock()
display_subscribers = []

# Customer display config
def load_display_config():
    """Load customer display configuration from Django API"""
    # Reuse launcher config.json (no need for separate file)
    config_path = Path(__file__).parent / 'config.json'
    
    # Default connection info (fallback)
    edge_server = 'http://127.0.0.1:8001'
    company_code = 'YOGYA'
    brand_code = 'BOE'
    store_code = 'KPT'
    
    print("=" * 70)
    print("[Config] Loading Customer Display Configuration...")
    
    # Try to load connection info from config.json
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            json_config = json.load(f)
            edge_server = json_config.get('edge_server', edge_server)
            company_code = json_config.get('company_code', company_code)
            brand_code = json_config.get('brand_code', brand_code)
            store_code = json_config.get('store_code', store_code)
            print(f"[Config] Connection info from config.json: {edge_server}")
    except Exception as e:
        print(f"[Config] WARNING: Could not load config.json: {e}")
        print(f"[Config] Using hardcoded defaults: {edge_server}")
    
    # Try to fetch config from Django API (DATABASE)
    try:
        import requests
        api_url = f"{edge_server}/api/customer-display/slideshow"
        params = {
            'company': company_code,
            'brand': brand_code,
            'store': store_code
        }
        
        print(f"[Config] Fetching from Django API (Database)...")
        print(f"[Config] URL: {api_url}")
        print(f"[Config] Params: company={company_code}, brand={brand_code}, store={store_code}")
        
        response = requests.get(api_url, params=params, timeout=3)
        if response.status_code == 200:
            api_data = response.json()
            if api_data.get('success'):
                print(f"[Config] SUCCESS - Config loaded from DATABASE!")
                print(f"[Config] Brand: {api_data.get('brand', {}).get('name', 'N/A')}")
                print(f"[Config] Slides: {len(api_data.get('slides', []))} items")
                print(f"[Config] Running Text: {len(api_data.get('running_text', ''))} chars")
                print(f"[Config] Theme: {api_data.get('theme', {}).get('primary_color', 'N/A')}")
                print("=" * 70)
                return {
                    'edge_server': edge_server,
                    'company_code': company_code,
                    'brand_code': brand_code,
                    'store_code': store_code,
                    'brand': api_data.get('brand', {}),
                    'slideshow': api_data.get('slides', []),
                    'running_text': api_data.get('running_text', ''),
                    'running_text_speed': api_data.get('running_text_speed', 80),
                    'theme': api_data.get('theme', {})
                }
        print(f"[Config] WARNING: API returned status {response.status_code}")
    except Exception as e:
        print(f"[Config] ERROR: Error fetching from Django API: {e}")
    
    # Fallback to JSON file
    print(f"[Config] Falling back to JSON file...")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            print(f"[Config] WARNING: Using STATIC JSON file config (not from database)")
            print("=" * 70)
            return json.load(f)
    except Exception as e:
        print(f"[Config] ERROR: Error loading JSON file: {e}")
        print(f"[Config] Using hardcoded defaults")
        print("=" * 70)
        return {
            'edge_server': edge_server,
            'company_code': company_code,
            'brand_code': brand_code,
            'store_code': store_code,
            'brand': {'name': 'POS System', 'logo_url': None, 'tagline': ''},
            'slideshow': [],
            'running_text': 'Welcome!',
            'running_text_speed': 80,
            'theme': {
                'primary_color': '#667eea',
                'secondary_color': '#764ba2',
                'text_color': '#ffffff',
                'billing_bg': 'rgba(255,255,255,0.95)',
                'billing_text': '#333333'
            }
        }


def print_to_local_printer(data):
    """Print to local printer (Windows/Linux compatible)"""
    system = platform.system()
    
    try:
        if system == 'Windows':
            return print_windows(data)
        elif system == 'Linux':
            return print_linux(data)
        else:
            return {'success': False, 'error': f'Unsupported platform: {system}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def print_windows(data):
    """Windows printing using win32print"""
    try:
        import win32print
        import win32ui
        from PIL import Image, ImageDraw, ImageFont
        
        printer_name = data.get('printer_name') or win32print.GetDefaultPrinter()
        
        # Create printer DC
        hprinter = win32print.OpenPrinter(printer_name)
        
        # For receipt printers, send raw ESC/POS commands
        if data.get('type') == 'receipt':
            raw_data = generate_receipt_escpos(data)
            win32print.StartDocPrinter(hprinter, 1, ("Receipt", None, "RAW"))
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, raw_data)
            win32print.EndPagePrinter(hprinter)
            win32print.EndDocPrinter(hprinter)
        
        win32print.ClosePrinter(hprinter)
        
        return {'success': True, 'printer': printer_name}
    except ImportError:
        return {'success': False, 'error': 'win32print not installed'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def print_linux(data):
    """Linux printing using CUPS"""
    try:
        import cups
        
        conn = cups.Connection()
        printers = conn.getPrinters()
        
        printer_name = data.get('printer_name') or list(printers.keys())[0]
        
        # For receipt printers, send raw ESC/POS
        if data.get('type') == 'receipt':
            raw_data = generate_receipt_escpos(data)
            
            # Create temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.prn') as f:
                f.write(raw_data)
                temp_path = f.name
            
            # Print raw file
            job_id = conn.printFile(printer_name, temp_path, "POS Receipt", {
                'raw': 'True'
            })
            
            import os
            os.unlink(temp_path)
            
            return {'success': True, 'printer': printer_name, 'job_id': job_id}
        
        return {'success': False, 'error': 'Print type not supported'}
    except ImportError:
        return {'success': False, 'error': 'pycups not installed'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def generate_receipt_escpos(data):
    """Generate ESC/POS commands for receipt"""
    # ESC/POS basic commands
    ESC = b'\x1b'
    INIT = ESC + b'@'
    ALIGN_CENTER = ESC + b'a\x01'
    ALIGN_LEFT = ESC + b'a\x00'
    BOLD_ON = ESC + b'E\x01'
    BOLD_OFF = ESC + b'E\x00'
    CUT = ESC + b'd\x03' + ESC + b'i'  # Feed and cut
    
    receipt = INIT + ALIGN_LEFT
    
    # Check if we received pre-rendered text (new format)
    if 'text' in data:
        print("[Print] Using pre-rendered receipt text")
        receipt_text = data.get('text', '')
        
        # Process the rendered text
        # Replace [CUT] marker with actual cut command
        receipt_text = receipt_text.replace('[CUT]', '')
        
        # Encode to bytes
        receipt += receipt_text.encode('utf-8', errors='replace')
        
        # Auto-cut if requested
        if data.get('auto_cut', True):
            receipt += CUT
        
        return receipt
    
    # Legacy format (JSON data) - keep for backward compatibility
    print("[Print] Using legacy JSON format")
    
    # Header
    receipt += ALIGN_CENTER + BOLD_ON
    receipt += data.get('store_name', 'STORE').encode('utf-8') + b'\n'
    receipt += BOLD_OFF
    receipt += data.get('store_address', '').encode('utf-8') + b'\n'
    receipt += b'=' * 42 + b'\n'
    
    # Items
    receipt += ALIGN_LEFT
    for item in data.get('items', []):
        name = item.get('name', '')[:30]
        qty = item.get('quantity', 1)
        price = item.get('price', 0)
        total = qty * price
        
        receipt += f"{name}\n".encode('utf-8')
        receipt += f"  {qty} x {price:,.0f} = {total:,.0f}\n".encode('utf-8')
    
    receipt += b'=' * 42 + b'\n'
    
    # Total
    receipt += BOLD_ON
    receipt += f"TOTAL: Rp {data.get('total', 0):,.0f}\n".encode('utf-8')
    receipt += BOLD_OFF
    
    receipt += b'\n' * 3
    receipt += ALIGN_CENTER
    receipt += b'Thank you!\n'
    receipt += b'\n' * 2
    
    # Cut paper
    receipt += CUT
    
    return receipt


@app.route('/', methods=['GET'])
def api_dashboard():
    """API Dashboard - Show all available endpoints"""
    
    # Get all routes and organize them
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            routes.append({
                'endpoint': rule.rule,
                'methods': ', '.join([m for m in rule.methods if m not in ['HEAD', 'OPTIONS']]),
                'function': rule.endpoint
            })
    
    # Sort by endpoint
    routes.sort(key=lambda x: x['endpoint'])
    
    # Create HTML dashboard
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local API Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        
        .header h1 {
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .header p {
            font-size: 18px;
            opacity: 0.95;
        }
        
        .status-card {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-box .label {
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 8px;
        }
        
        .stat-box .value {
            font-size: 32px;
            font-weight: 700;
        }
        
        .endpoints-card {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .endpoints-card h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 24px;
        }
        
        .endpoint {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.3s ease;
            background: #fafafa;
        }
        
        .endpoint:hover {
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
            background: white;
        }
        
        .endpoint-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        
        .endpoint-path {
            font-family: 'Courier New', monospace;
            font-size: 16px;
            font-weight: 600;
            color: #333;
        }
        
        .methods {
            display: flex;
            gap: 8px;
        }
        
        .method {
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        
        .method.GET {
            background: #4caf50;
            color: white;
        }
        
        .method.POST {
            background: #2196f3;
            color: white;
        }
        
        .method.PUT {
            background: #ff9800;
            color: white;
        }
        
        .method.DELETE {
            background: #f44336;
            color: white;
        }
        
        .endpoint-description {
            color: #666;
            font-size: 14px;
            margin-top: 8px;
            line-height: 1.5;
        }
        
        .test-button {
            margin-top: 12px;
            padding: 8px 16px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .test-button:hover {
            background: #764ba2;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
        }
        
        .quick-links {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .quick-link {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-decoration: none;
            color: #333;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            text-align: center;
        }
        
        .quick-link:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
        }
        
        .quick-link-icon {
            font-size: 32px;
            margin-bottom: 10px;
        }
        
        .quick-link-title {
            font-weight: 600;
            font-size: 16px;
            color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Local API Server</h1>
            <p>POS Launcher & Customer Display API</p>
        </div>
        
        <div class="status-card">
            <h2 style="color: #333; margin-bottom: 15px;">Server Status</h2>
            <div class="status-grid">
                <div class="stat-box">
                    <div class="label">Status</div>
                    <div class="value">✓ Online</div>
                </div>
                <div class="stat-box">
                    <div class="label">Port</div>
                    <div class="value">5000</div>
                </div>
                <div class="stat-box">
                    <div class="label">Platform</div>
                    <div class="value">""" + platform.system() + """</div>
                </div>
                <div class="stat-box">
                    <div class="label">Endpoints</div>
                    <div class="value">""" + str(len(routes)) + """</div>
                </div>
            </div>
        </div>
        
        <div class="quick-links">
            <a href="/customer-display" class="quick-link">
                <div class="quick-link-icon">🖥️</div>
                <div class="quick-link-title">Customer Display</div>
            </a>
            <a href="/health" class="quick-link">
                <div class="quick-link-icon">❤️</div>
                <div class="quick-link-title">Health Check</div>
            </a>
            <a href="/api/customer-display/config" class="quick-link">
                <div class="quick-link-icon">⚙️</div>
                <div class="quick-link-title">Display Config</div>
            </a>
        </div>
        
        <div class="endpoints-card">
            <h2>📡 Available API Endpoints</h2>
"""
    
    # Add endpoint descriptions
    endpoint_docs = {
        '/': 'API Dashboard - This page',
        '/customer-display': 'Customer Display HTML interface',
        '/assets/<path:filename>': 'Serve static assets (CSS, JS, images)',
        '/health': 'Health check endpoint',
        '/api/customer-display/config': 'Get customer display configuration from Django',
        '/api/customer-display/qr': 'Generate QR code for payment',
        '/api/customer-display/hide-qr': 'Hide QR code and return to normal display',
        '/api/customer-display/update': 'Update customer display data (bill panel, modal)',
        '/api/customer-display/stream': 'SSE stream for real-time updates',
        '/api/print': 'Print to local printer'
    }
    
    for route in routes:
        endpoint = route['endpoint']
        methods = route['methods'].split(', ')
        description = endpoint_docs.get(endpoint, 'No description available')
        
        html += f"""
            <div class="endpoint">
                <div class="endpoint-header">
                    <div class="endpoint-path">{endpoint}</div>
                    <div class="methods">
"""
        
        for method in methods:
            html += f'                        <span class="method {method}">{method}</span>\n'
        
        html += f"""
                    </div>
                </div>
                <div class="endpoint-description">{description}</div>
"""
        
        # Add test button for GET endpoints
        if 'GET' in methods and endpoint not in ['/', '/assets/<path:filename>']:
            html += f"""
                <button class="test-button" onclick="window.open('{endpoint}', '_blank')">
                    Test Endpoint →
                </button>
"""
        
        html += """
            </div>
"""
    
    html += """
        </div>
    </div>
    
    <script>
        // Auto-refresh status every 30 seconds
        setInterval(() => {
            fetch('/health')
                .then(r => r.json())
                .then(data => console.log('Health check:', data))
                .catch(e => console.error('Health check failed:', e));
        }, 30000);
    </script>
</body>
</html>
"""
    
    return html


@app.route('/customer-display', methods=['GET'])
def serve_customer_display():
    """Serve customer display HTML"""
    print(f"[API] Received request: GET /customer-display from {request.remote_addr}")
    try:
        html_path = Path(__file__).parent / 'customer_display.html'
        print(f"[DEBUG] Serving HTML from: {html_path}")
        print(f"[DEBUG] File exists: {html_path.exists()}")
        
        if html_path.exists():
            print(f"[API] Successfully serving customer_display.html")
            return send_file(str(html_path))
        else:
            print(f"[ERROR] customer_display.html not found at {html_path}")
            return jsonify({'error': 'customer_display.html not found', 'path': str(html_path)}), 404
    except Exception as e:
        print(f"[ERROR] Exception serving HTML: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/assets/<path:filename>', methods=['GET'])
def serve_assets(filename):
    """Serve static assets (CSS, JS, images) for offline use"""
    try:
        assets_dir = Path(__file__).parent / 'assets'
        file_path = assets_dir / filename
        
        print(f"[DEBUG] Serving asset: {filename}")
        print(f"[DEBUG] Full path: {file_path}")
        print(f"[DEBUG] File exists: {file_path.exists()}")
        
        if file_path.exists() and file_path.is_file():
            # Security: Ensure file is within assets directory (prevent path traversal)
            if not str(file_path.resolve()).startswith(str(assets_dir.resolve())):
                print(f"[SECURITY] Path traversal attempt blocked: {filename}")
                return jsonify({'error': 'Invalid path'}), 403
            
            return send_file(str(file_path))
        else:
            print(f"[ERROR] Asset not found: {filename}")
            return jsonify({'error': 'Asset not found', 'path': str(file_path)}), 404
    except Exception as e:
        print(f"[ERROR] Exception serving asset: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/favicon.ico', methods=['GET'])
def favicon():
    """Return 204 No Content for favicon requests to avoid 404 spam"""
    return '', 204


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'platform': platform.system(),
        'timestamp': time.time()
    })


@app.route('/api/customer-display/config', methods=['GET'])
def get_display_config():
    """Get customer display configuration"""
    print(f"[API] Received request: GET /api/customer-display/config from {request.remote_addr}")
    try:
        config = load_display_config()
        print(f"[API] Successfully loaded config, returning {len(str(config))} chars")
        return jsonify(config)
    except Exception as e:
        print(f"[ERROR] Exception in get_display_config: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'brand': {'name': 'POS System', 'logo_url': None, 'tagline': ''},
            'slideshow': [],
            'running_text': 'Welcome!',
            'running_text_speed': 80,
            'theme': {
                'primary_color': '#667eea',
                'secondary_color': '#764ba2',
                'text_color': '#ffffff',
                'billing_bg': 'rgba(255,255,255,0.95)',
                'billing_text': '#333333'
            }
        }), 500


@app.route('/api/customer-display/qr', methods=['POST'])
def generate_qr_code():
    """Generate QR code for payment"""
    if not QRCODE_AVAILABLE:
        return jsonify({'success': False, 'error': 'QR code library not available'}), 500
    
    data = request.json
    qr_data = data.get('qr_data') or data.get('payment_url') or data.get('bill_number')
    
    if not qr_data:
        return jsonify({'success': False, 'error': 'No QR data provided'}), 400
    
    try:
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(str(qr_data))
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 data URL
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode()
        qr_code_url = f'data:image/png;base64,{img_base64}'
        
        # Update display data to show QR
        with display_lock:
            display_data['show_qr'] = True
            display_data['qr_code'] = qr_code_url
            display_data['total'] = data.get('total', display_data.get('total', 0))
            display_data['payment_method'] = data.get('payment_method', 'QRIS')
            display_data['updated_at'] = time.time()
        
        # Notify subscribers
        notify_subscribers(display_data)
        
        return jsonify({
            'success': True,
            'qr_code': qr_code_url
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/customer-display/hide-qr', methods=['POST'])
def hide_qr_code():
    """Hide QR code and return to normal display"""
    with display_lock:
        display_data['show_qr'] = False
        display_data['qr_code'] = None
        display_data['updated_at'] = time.time()
    
    # Notify subscribers
    notify_subscribers(display_data)
    
    return jsonify({'success': True})


@app.route('/api/print', methods=['POST'])
def api_print():
    """Print endpoint"""
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    result = print_to_local_printer(data)
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@app.route('/api/customer-display/update', methods=['POST'])
def update_customer_display():
    """Update customer display data"""
    global display_data
    
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    with display_lock:
        # Check if we're receiving modal HTML
        if 'show_modal' in data:
            display_data['show_modal'] = data.get('show_modal', False)
            display_data['modal_html'] = data.get('modal_html', None)
            display_data['updated_at'] = time.time()
            print(f"[Modal Update] show_modal={data.get('show_modal')}, modal_html_length={len(data.get('modal_html', '')) if data.get('modal_html') else 0}")
        # Check if we're receiving bill panel HTML (new format)
        elif 'bill_panel_html' in data:
            display_data['bill_panel_html'] = data.get('bill_panel_html')
            display_data['has_bill'] = data.get('has_bill', False)
            display_data['updated_at'] = time.time()
        else:
            # Legacy format (JSON data only) - keep for backward compatibility
            display_data = {
                'total': data.get('total', 0),
                'items': data.get('items', []),
                'customer_name': data.get('customer_name', ''),
                'payment_method': data.get('payment_method', ''),
                'change': data.get('change', 0),
                'has_bill': len(data.get('items', [])) > 0,
                'bill_panel_html': None,
                'show_modal': False,
                'modal_html': None,
                'updated_at': time.time()
            }
    
    # Notify all SSE subscribers
    notify_subscribers(display_data)
    
    return jsonify({'success': True})


@app.route('/api/customer-display/stream', methods=['GET'])
def customer_display_stream():
    """SSE stream for customer display"""
    
    def event_stream():
        try:
            # Send initial state
            with display_lock:
                initial_data = dict(display_data)
            yield f"data: {json.dumps(initial_data)}\n\n"
            
            # Create queue for this subscriber
            q = queue.Queue()
            display_subscribers.append(q)
            
            print(f"[SSE] New subscriber connected (total: {len(display_subscribers)})")
            
            try:
                while True:
                    # Wait for updates with timeout to avoid hanging
                    try:
                        data = q.get(timeout=30)
                        yield f"data: {json.dumps(data)}\n\n"
                    except queue.Empty:
                        # Send keepalive ping
                        yield ": keepalive\n\n"
            except GeneratorExit:
                # Client disconnected
                if q in display_subscribers:
                    display_subscribers.remove(q)
                print(f"[SSE] Subscriber disconnected (remaining: {len(display_subscribers)})")
        except Exception as e:
            print(f"[SSE] Error in event stream: {e}")
            if q in display_subscribers:
                display_subscribers.remove(q)
    
    response = Response(event_stream(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


def notify_subscribers(data):
    """Notify all SSE subscribers of data update"""
    for q in display_subscribers[:]:  # Copy list to avoid modification during iteration
        try:
            q.put_nowait(data)
        except:
            # Remove dead subscriber
            display_subscribers.remove(q)


@app.route('/print-monitor')
def print_monitor_dashboard():
    """Serve print job monitoring dashboard"""
    html_file = Path(__file__).parent / 'print_monitor.html'
    
    if html_file.exists():
        return send_file(str(html_file))
    else:
        # Return inline HTML if file doesn't exist
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Print Monitor</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #333; }
        .alert { padding: 15px; background: #f44336; color: white; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Print Monitor</h1>
        <div class="alert">
            Error: print_monitor.html not found. Please create the file.
        </div>
    </div>
</body>
</html>
        """


@app.route('/api/print-jobs')
def get_print_jobs():
    """Get print jobs from Django API and return as JSON"""
    import requests
    
    try:
        # Get Django base URL from config
        django_url = os.environ.get('DJANGO_URL', 'http://127.0.0.1:8001')
        
        # Forward request params
        status_filter = request.args.get('status', 'all')
        limit = request.args.get('limit', '50')
        
        # Call Django API
        response = requests.get(
            f'{django_url}/pos/api/print-jobs/',
            params={'status': status_filter, 'limit': limit},
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'success': False,
                'error': f'Django API returned {response.status_code}',
                'jobs': [],
                'count': 0
            }), 500
    
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'error': 'Cannot connect to Django (http://127.0.0.1:8001)',
            'jobs': [],
            'count': 0
        }), 503
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'jobs': [],
            'count': 0
        }), 500


@app.route('/api/print-jobs/<int:job_id>/retry', methods=['POST'])
def retry_print_job(job_id):
    """Retry a failed print job"""
    import requests
    
    try:
        # Get Django URL
        django_url = os.environ.get('DJANGO_URL', 'http://127.0.0.1:8001')
        
        # Get job details from Django
        response = requests.get(
            f'{django_url}/pos/api/print-jobs/',
            params={'limit': 1000},
            timeout=5
        )
        
        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Failed to get job details'}), 500
        
        jobs = response.json().get('jobs', [])
        job = next((j for j in jobs if j['id'] == job_id), None)
        
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        # Retry print by calling /api/print endpoint
        # Note: This is simplified - in production you'd get full job content from Django
        print_response = requests.post(
            'http://127.0.0.1:5000/api/print',
            json={
                'type': job['job_type'],
                'text': f"Retry Print Job #{job_id}\nBill: {job['bill_number']}\n",
                'auto_cut': True
            },
            timeout=3
        )
        
        if print_response.status_code == 200:
            return jsonify({'success': True, 'message': 'Print job retried'})
        else:
            return jsonify({'success': False, 'error': 'Print failed'}), 500
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def run_server(host='127.0.0.1', port=5000):
    """Run Flask server"""
    print(f"[Local API] Starting on {host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == '__main__':
    run_server()
