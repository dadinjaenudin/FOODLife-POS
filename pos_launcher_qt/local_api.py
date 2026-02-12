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

try:
    from PIL import Image
    import requests
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[Warning] PIL library not installed. Logo printing disabled.")
    print("[Warning] Install with: pip install Pillow requests")

app = Flask(__name__)
CORS(app)  # Allow requests from webview

# 404 handler - Don't spam logs for browser requests like favicon
@app.errorhandler(404)
def handle_404(e):
    """Handle 404 errors silently for common browser requests"""
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
    'show_review': False,
    'review_bill_id': None,
    'updated_at': time.time()
}
display_lock = Lock()
display_subscribers = []

# Customer display config
def load_display_config():
    """Load customer display configuration from Django API"""
    # Load config.json from same directory as POSLauncher.exe
    config_path = Path(os.getcwd()) / 'config.json'
    
    # Default connection info (fallback)
    edge_server = 'http://127.0.0.1:8001'
    company_code = 'YOGYA'
    brand_code = 'BOE'
    store_code = 'KPT'
    
    # Try to load connection info from config.json
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            json_config = json.load(f)
            edge_server = json_config.get('edge_server', edge_server)
            company_code = json_config.get('company_code', company_code)
            brand_code = json_config.get('brand_code', brand_code)
            store_code = json_config.get('store_code', store_code)
    except Exception as e:
        print(f"[Config] Warning: Could not load config.json: {e}")
    
    # Fetch display config from Edge Server (branding, running text, theme)
    display_config = None
    try:
        import requests
        config_api_url = f"{edge_server}/api/customer-display/config"
        config_params = {
            'company': company_code,
            'brand': brand_code,
            'store': store_code
        }
        
        config_response = requests.get(config_api_url, params=config_params, timeout=5)
        if config_response.status_code == 200:
            config_data = config_response.json()
            if config_data.get('success'):
                display_config = config_data.get('config', {})
    except Exception as e:
        print(f"[Config] Display config API error: {e}")
    
    # Fetch slideshow from Edge Server
    slideshow_data = []
    try:
        import requests
        slideshow_api_url = f"{edge_server}/api/customer-display/slideshow"
        slideshow_params = {
            'company': company_code,
            'brand': brand_code,
            'store': store_code
        }
        
        slideshow_response = requests.get(slideshow_api_url, params=slideshow_params, timeout=5)
        if slideshow_response.status_code == 200:
            slideshow_json = slideshow_response.json()
            if slideshow_json.get('success'):
                slideshow_data = slideshow_json.get('slides', [])
    except Exception as e:
        print(f"[Config] Slideshow API error: {e}")
    
    # Helper: Convert relative URLs to absolute URLs
    def make_absolute_url(url, base_server):
        """
        Convert relative URLs to absolute URLs
        Also replaces localhost URLs with actual edge server host
        """
        if not url:
            return url
        
        # Replace localhost:9002 (MinIO hardcoded) with edge server host
        # This handles URLs like: http://localhost:9002/customer-display/image.jpg
        if 'localhost:9002' in url or '127.0.0.1:9002' in url:
            # Extract edge server host (without the port)
            # Example: http://192.168.1.100:8001 -> http://192.168.1.100:9002
            if base_server.startswith('http://') or base_server.startswith('https://'):
                # Parse edge server to get host and replace port
                from urllib.parse import urlparse
                parsed = urlparse(base_server)
                # Build MinIO URL with same host but port 9002
                minio_base = f"{parsed.scheme}://{parsed.hostname}:9002"
                # Replace localhost with actual host
                url = url.replace('http://localhost:9002', minio_base)
                url = url.replace('http://127.0.0.1:9002', minio_base)
                return url
        
        # Already absolute URL (and not localhost:9002)
        if url.startswith('http://') or url.startswith('https://'):
            return url
        
        # Relative URL - make absolute
        if url.startswith('/'):
            return f"{base_server}{url}"
        return f"{base_server}/{url}"
    
    # Combine config and slideshow data
    if display_config:
        # Fix brand logo URL
        brand_logo = display_config.get('brand_logo_url')
        if brand_logo:
            brand_logo = make_absolute_url(brand_logo, edge_server)

        # Fix store image URL (for idle/waiting state)
        store_image = display_config.get('store_image_url')
        if store_image:
            store_image = make_absolute_url(store_image, edge_server)

        # Fix slideshow image URLs
        for slide in slideshow_data:
            if 'image_url' in slide:
                slide['image_url'] = make_absolute_url(slide['image_url'], edge_server)
        
        result = {
            'edge_server': edge_server,
            'company_code': company_code,
            'brand_code': brand_code,
            'store_code': store_code,
            'brand': {
                'name': display_config.get('brand_name', 'POS System'),
                'logo_url': brand_logo,
                'tagline': display_config.get('brand_tagline', '')
            },
            'store_image_url': store_image,
            'slideshow': slideshow_data,
            'running_text': display_config.get('running_text', 'Welcome!'),
            'running_text_speed': display_config.get('running_text_speed', 50),
            'theme': display_config.get('theme', {
                'primary_color': '#667eea',
                'secondary_color': '#764ba2',
                'text_color': '#ffffff',
                'billing_bg': 'rgba(255,255,255,0.95)',
                'billing_text': '#333333'
            })
        }
        
        return result
    
    # Fallback to default config
    return {
        'edge_server': edge_server,
        'company_code': company_code,
        'brand_code': brand_code,
        'store_code': store_code,
        'brand': {'name': 'POS System', 'logo_url': None, 'tagline': ''},
        'slideshow': slideshow_data if slideshow_data else [],
        'running_text': 'Welcome!',
        'running_text_speed': 50,
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


def image_to_escpos_bitmap(image, max_width=384):
    """Convert PIL Image to ESC/POS bitmap format
    
    Args:
        image: PIL Image object
        max_width: Maximum width in pixels (58mm = ~384px, 80mm = ~576px)
    
    Returns:
        bytes: ESC/POS bitmap commands
    """
    try:
        # Convert to grayscale
        image = image.convert('L')
        
        # Resize to fit paper width
        width, height = image.size
        if width > max_width:
            ratio = max_width / width
            new_size = (max_width, int(height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            width, height = image.size
        
        # Convert to 1-bit (black and white)
        image = image.convert('1')
        
        # Get pixel data
        pixels = list(image.getdata())
        
        # ESC/POS bitmap command: ESC * m nL nH [data]
        # m = mode (33 = 24-dot double density)
        ESC = b'\x1b'
        
        # Build bitmap data line by line (24 dots vertical)
        bitmap_data = b''
        
        # Process in bands of 24 pixels height
        for y in range(0, height, 24):
            # Line start: ESC * 33 (24-dot double density)
            # Width in bytes
            n = width
            nL = n & 0xFF
            nH = (n >> 8) & 0xFF
            
            line_data = ESC + b'*' + bytes([33, nL, nH])
            
            # Process each column (24 vertical pixels per column)
            for x in range(width):
                # Collect 24 vertical pixels into 3 bytes
                bytes_data = [0, 0, 0]
                
                for k in range(24):
                    if y + k < height:
                        pixel_idx = (y + k) * width + x
                        if pixel_idx < len(pixels):
                            pixel = pixels[pixel_idx]
                            # If pixel is black (0), set bit
                            if pixel == 0:
                                byte_idx = k // 8
                                bit_idx = 7 - (k % 8)
                                bytes_data[byte_idx] |= (1 << bit_idx)
                
                line_data += bytes(bytes_data)
            
            line_data += b'\n'
            bitmap_data += line_data
        
        return bitmap_data
        
    except Exception as e:
        print(f"[Error] Failed to convert image to ESC/POS: {e}")
        return b''


def download_and_process_logo(logo_url, edge_server, paper_width=58):
    """Download logo from URL and convert to ESC/POS bitmap
    
    Args:
        logo_url: Relative or absolute URL to download logo from
        edge_server: Edge server base URL (from config.json)
        paper_width: Paper width in mm (58 or 80)
    
    Returns:
        bytes: ESC/POS bitmap commands or empty bytes if failed
    """
    if not PIL_AVAILABLE:
        print("[Warning] PIL not available, cannot process logo")
        return b''
    
    try:
        # Build full URL if logo_url is relative path
        if logo_url.startswith('/'):
            full_url = edge_server + logo_url
        else:
            full_url = logo_url
        
        # Download image
        response = requests.get(full_url, timeout=5)
        response.raise_for_status()
        
        # Open image
        image = Image.open(BytesIO(response.content))
        
        # Convert paper width to pixels (58mm = ~384px, 80mm = ~576px)
        max_width = 384 if paper_width == 58 else 576
        
        # Convert to ESC/POS bitmap
        bitmap_data = image_to_escpos_bitmap(image, max_width)
        
        return bitmap_data
        
    except Exception as e:
        print(f"[Error] Failed to download/process logo: {e}")
        return b''


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
        receipt_text = data.get('text', '')
        
        # Check for logo marker and insert actual logo image
        if '[LOGO_START]' in receipt_text and '[LOGO_END]' in receipt_text:
            logo_data = data.get('logo_data', b'')
            
            if logo_data:
                # Split text at logo marker
                parts = receipt_text.split('[LOGO_START]')
                before_logo = parts[0]
                after_logo = parts[1].split('[LOGO_END]')[1] if '[LOGO_END]' in parts[1] else parts[1]
                
                # Build receipt with logo
                receipt += before_logo.encode('utf-8', errors='replace')
                receipt += ALIGN_CENTER
                receipt += logo_data
                receipt += ALIGN_LEFT
                receipt += after_logo.encode('utf-8', errors='replace')
            else:
                # No logo data, just remove markers
                receipt_text = receipt_text.replace('[LOGO_START]', '').replace('[LOGO_END]', '')
                receipt += receipt_text.encode('utf-8', errors='replace')
        else:
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
    try:
        html_path = Path(__file__).parent / 'customer_display.html'

        if html_path.exists():
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


@app.route('/api/printer/status', methods=['GET'])
def printer_status():
    """Check actual printer hardware status.

    Returns printer name, connection status, and any error conditions.
    Uses win32print on Windows and CUPS on Linux to query the physical printer.

    Response:
    {
        "printer_name": "EPSON TM-T82",
        "printer_status": "ready",       // ready | offline | error | warning | unknown
        "status_code": 0,                // raw status bitmask (Windows)
        "status_flags": [],              // human-readable list of active flags
        "message": "Printer Ready"       // display message
    }
    """
    system = platform.system()

    try:
        if system == 'Windows':
            return jsonify(_get_printer_status_windows())
        elif system == 'Linux':
            return jsonify(_get_printer_status_linux())
        else:
            return jsonify({
                'printer_name': None,
                'printer_status': 'unknown',
                'status_code': -1,
                'status_flags': [],
                'message': f'Unsupported platform: {system}'
            })
    except Exception as e:
        return jsonify({
            'printer_name': None,
            'printer_status': 'error',
            'status_code': -1,
            'status_flags': [],
            'message': str(e)
        })


def _get_printer_status_windows():
    """Query printer hardware status on Windows using win32print"""
    try:
        import win32print
    except ImportError:
        return {
            'printer_name': None,
            'printer_status': 'error',
            'status_code': -1,
            'status_flags': [],
            'message': 'win32print not installed'
        }

    try:
        printer_name = win32print.GetDefaultPrinter()
    except Exception:
        return {
            'printer_name': None,
            'printer_status': 'offline',
            'status_code': -1,
            'status_flags': [],
            'message': 'No default printer configured'
        }

    # Status flag definitions (win32print constants)
    STATUS_FLAGS = {
        0x00000002: 'error',
        0x00000008: 'paper_jam',
        0x00000010: 'paper_out',
        0x00000040: 'paper_problem',
        0x00000080: 'offline',
        0x00000200: 'busy',
        0x00000400: 'printing',
        0x00001000: 'not_available',
        0x00008000: 'initializing',
        0x00010000: 'warming_up',
        0x00020000: 'toner_low',
        0x00040000: 'no_toner',
        0x00100000: 'user_intervention',
        0x00400000: 'door_open',
        0x01000000: 'power_save',
    }

    # Human-readable messages for status flags
    STATUS_MESSAGES = {
        'error': 'Printer Error',
        'paper_jam': 'Paper Jam',
        'paper_out': 'Paper Out',
        'paper_problem': 'Paper Problem',
        'offline': 'Printer Offline',
        'busy': 'Printer Busy',
        'printing': 'Printing...',
        'not_available': 'Printer Not Available',
        'initializing': 'Initializing...',
        'warming_up': 'Warming Up...',
        'toner_low': 'Toner Low',
        'no_toner': 'No Toner',
        'user_intervention': 'User Intervention Required',
        'door_open': 'Cover Open',
        'power_save': 'Power Save Mode',
    }

    hprinter = None
    try:
        hprinter = win32print.OpenPrinter(printer_name)
        # GetPrinter level 2 includes Status field
        printer_info = win32print.GetPrinter(hprinter, 2)
        status_code = printer_info.get('Status', 0) if isinstance(printer_info, dict) else printer_info[18]

        # Decode status flags
        active_flags = []
        for flag_bit, flag_name in STATUS_FLAGS.items():
            if status_code & flag_bit:
                active_flags.append(flag_name)

        # Determine overall status
        error_flags = {'error', 'paper_jam', 'paper_out', 'paper_problem', 'offline',
                       'not_available', 'no_toner', 'user_intervention'}
        warning_flags = {'door_open', 'toner_low', 'power_save'}
        busy_flags = {'busy', 'printing', 'initializing', 'warming_up'}

        if status_code == 0:
            # Spooler says OK - but verify physical connectivity via WMI.
            # win32print.GetPrinter often reports status=0 even when USB is unplugged
            # because the printer driver is still installed. WMI detects actual disconnection.
            wmi_result = _wmi_printer_check(printer_name)
            if wmi_result == 'offline':
                printer_status = 'offline'
                message = 'Printer Disconnected'
                active_flags = ['offline']
            else:
                printer_status = 'ready'
                message = 'Printer Ready'
        elif any(f in error_flags for f in active_flags):
            printer_status = 'offline'
            # Use the first error flag's message
            for f in active_flags:
                if f in error_flags:
                    message = STATUS_MESSAGES.get(f, 'Printer Error')
                    break
            else:
                message = 'Printer Error'
        elif any(f in warning_flags for f in active_flags):
            printer_status = 'warning'
            message = STATUS_MESSAGES.get(active_flags[0], 'Warning')
        elif any(f in busy_flags for f in active_flags):
            printer_status = 'ready'
            message = STATUS_MESSAGES.get(active_flags[0], 'Busy')
        else:
            printer_status = 'ready'
            message = 'Printer Ready'

        return {
            'printer_name': printer_name,
            'printer_status': printer_status,
            'status_code': status_code,
            'status_flags': active_flags,
            'message': message
        }
    except Exception as e:
        return {
            'printer_name': printer_name,
            'printer_status': 'offline',
            'status_code': -1,
            'status_flags': [],
            'message': f'Cannot query printer: {str(e)}'
        }
    finally:
        if hprinter is not None:
            try:
                win32print.ClosePrinter(hprinter)
            except Exception:
                pass


def _wmi_printer_check(printer_name):
    """Use WMI via COM to detect physical printer connectivity (USB disconnection).

    win32print.GetPrinter() only queries the spooler which caches status.
    WMI Win32_Printer.WorkOffline detects actual USB disconnection.

    Returns: 'ready', 'offline', or None (if WMI check fails).
    """
    try:
        import pythoncom
        import win32com.client

        # COM must be initialized per-thread (Flask threaded=True)
        pythoncom.CoInitialize()
        result = 'offline'
        try:
            wmi = win32com.client.GetObject("winmgmts:")
            # Escape single quotes in printer name for WQL query
            escaped = printer_name.replace("\\", "\\\\").replace("'", "\\'")
            query = f"SELECT WorkOffline, PrinterStatus FROM Win32_Printer WHERE Name = '{escaped}'"
            printers = wmi.ExecQuery(query)

            for printer in printers:
                # WorkOffline = True when USB is physically disconnected
                if printer.WorkOffline:
                    result = 'offline'
                    break
                # PrinterStatus: 3=Idle, 4=Printing, 5=Warmup, 7=Offline
                elif printer.PrinterStatus == 7:
                    result = 'offline'
                    break
                else:
                    result = 'ready'
                    break

            # Explicitly release COM objects BEFORE CoUninitialize
            # to prevent "Win32 exception occurred releasing IUnknown" errors
            del printer
        except NameError:
            pass  # printer was never assigned (empty query result)
        finally:
            try:
                del printers
            except (NameError, UnboundLocalError):
                pass
            try:
                del wmi
            except (NameError, UnboundLocalError):
                pass
            # Force release any remaining COM pointers before uninitializing
            import gc
            gc.collect()
            pythoncom.CoUninitialize()

        return result
    except Exception as e:
        print(f"[Printer Status] WMI check failed: {e}")
        return None  # WMI unavailable, trust GetPrinter result


def _get_printer_status_linux():
    """Query printer hardware status on Linux using CUPS"""
    try:
        import cups
    except ImportError:
        return {
            'printer_name': None,
            'printer_status': 'error',
            'status_code': -1,
            'status_flags': [],
            'message': 'pycups not installed'
        }

    try:
        conn = cups.Connection()
        printers = conn.getPrinters()

        if not printers:
            return {
                'printer_name': None,
                'printer_status': 'offline',
                'status_code': -1,
                'status_flags': [],
                'message': 'No printers configured'
            }

        # Get default or first printer
        default_printer = conn.getDefault()
        printer_name = default_printer if default_printer else list(printers.keys())[0]
        printer_info = printers.get(printer_name, {})

        # CUPS printer states: 3=idle, 4=printing, 5=stopped
        state = printer_info.get('printer-state', 0)
        state_message = printer_info.get('printer-state-message', '')

        if state == 3:  # IPP_PRINTER_IDLE
            printer_status = 'ready'
            message = 'Printer Ready'
        elif state == 4:  # IPP_PRINTER_PROCESSING
            printer_status = 'ready'
            message = 'Printing...'
        elif state == 5:  # IPP_PRINTER_STOPPED
            printer_status = 'offline'
            message = state_message or 'Printer Stopped'
        else:
            printer_status = 'unknown'
            message = state_message or 'Unknown State'

        return {
            'printer_name': printer_name,
            'printer_status': printer_status,
            'status_code': state,
            'status_flags': [state_message] if state_message else [],
            'message': message
        }
    except Exception as e:
        return {
            'printer_name': None,
            'printer_status': 'error',
            'status_code': -1,
            'status_flags': [],
            'message': str(e)
        }


@app.route('/api/customer-display/config', methods=['GET'])
def get_display_config():
    """Get customer display configuration"""
    try:
        config = load_display_config()
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
        # Full display reset (single atomic clear — prevents flicker from multiple partial updates)
        if data.get('clear_display'):
            display_data.update({
                'items': [],
                'total': 0,
                'subtotal': 0,
                'customer_name': '',
                'show_qr': False,
                'qr_code': None,
                'payment_method': None,
                'bill_panel_html': None,
                'has_bill': False,
                'show_modal': False,
                'modal_html': None,
                'show_review': False,
                'review_bill_id': None,
                'updated_at': time.time()
            })
        # Check if we're triggering customer review
        elif 'show_review' in data:
            display_data['show_review'] = data.get('show_review', False)
            display_data['review_bill_id'] = data.get('bill_id')
            display_data['show_modal'] = False
            display_data['modal_html'] = None
            display_data['updated_at'] = time.time()
        # Check if we're receiving modal HTML
        elif 'show_modal' in data:
            display_data['show_modal'] = data.get('show_modal', False)
            display_data['modal_html'] = data.get('modal_html', None)
            display_data['show_review'] = False
            display_data['updated_at'] = time.time()
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
                'show_review': False,
                'updated_at': time.time()
            }

    # Notify all SSE subscribers
    notify_subscribers(display_data)

    return jsonify({'success': True})


@app.route('/api/customer-display/review', methods=['POST'])
def submit_review():
    """Proxy customer review from customer display to Django API"""
    data = request.json

    if not data or 'rating' not in data:
        return jsonify({'success': False, 'error': 'Rating is required'}), 400

    # Read edge server URL from config
    config_path = Path(os.getcwd()) / 'config.json'
    edge_server = 'http://127.0.0.1:8001'
    store_code = None
    terminal_code = None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            json_config = json.load(f)
            edge_server = json_config.get('edge_server', edge_server)
            store_code = json_config.get('store_code')
            terminal_code = json_config.get('terminal_code')
    except Exception:
        pass

    # Build payload for Django API
    payload = {
        'rating': data['rating'],
        'bill_id': data.get('bill_id'),
        'store_code': store_code,
        'terminal_code': terminal_code,
    }

    try:
        import requests as http_requests
        resp = http_requests.post(
            f"{edge_server}/api/customer-display/review/",
            json=payload,
            timeout=5
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        print(f"[Review] Failed to forward to Django: {e}")
        return jsonify({'success': False, 'error': str(e)}), 502


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


def fetch_receipt_template(edge_server, terminal_code, company_code=None, brand_code=None, store_code=None):
    """Fetch receipt template from Django API"""
    try:
        import requests
        
        # Build query params with all identifiers
        params = {'terminal_code': terminal_code}
        if company_code:
            params['company_code'] = company_code
        if brand_code:
            params['brand_code'] = brand_code
        if store_code:
            params['store_code'] = store_code
        
        response = requests.get(
            f"{edge_server}/api/terminal/receipt-template",
            params=params,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('template')
        
        return None
    except Exception as e:
        print(f"[Receipt Template] Error fetching template: {e}")
        return None


def format_receipt_text(bill_data, template):
    """Generate formatted receipt text from bill data and template"""
    lines = []
    # paper_width is in mm from terminal settings, convert to chars per line
    paper_width_mm = template.get('paper_width', 80)
    # Standard thermal printer: 58mm → 32 chars, 80mm → 42 chars
    if paper_width_mm <= 58:
        paper_width = 32
    else:
        paper_width = 42
    
    # Helper functions
    def center_text(text):
        text = str(text)
        if len(text) >= paper_width:
            return text[:paper_width]
        padding = (paper_width - len(text)) // 2
        return ' ' * padding + text
    
    def left_right_text(left, right):
        left = str(left)
        right = str(right)
        space = paper_width - len(left) - len(right)
        if space < 1:
            return left[:paper_width - len(right)] + right
        return left + ' ' * space + right
    
    def separator():
        return '=' * paper_width
    
    # Header with logo placeholder (will be replaced with actual image in ESC/POS generation)
    if template.get('show_logo') and template.get('logo_url'):
        lines.append('[LOGO_START]')
        lines.append('[LOGO_END]')
        lines.append('')
    
    # Header lines
    if template.get('header_line_1'):
        lines.append(center_text(template['header_line_1']))
    if template.get('header_line_2'):
        lines.append(center_text(template['header_line_2']))
    if template.get('header_line_3'):
        lines.append(center_text(template['header_line_3']))
    if template.get('header_line_4'):
        lines.append(center_text(template['header_line_4']))
    
    lines.append(separator())
    
    # Receipt info - aligned labels with consistent colon position
    label_width = 10  # Fixed width for labels to align colons
    
    if template.get('show_receipt_number'):
        lines.append(f"{'No':<{label_width}}: {bill_data.get('bill_number', '-')}")
    
    if template.get('show_date_time'):
        lines.append(f"{'Date':<{label_width}}: {bill_data.get('date', '-')}")
        lines.append(f"{'Time':<{label_width}}: {bill_data.get('time', '-')}")
    
    if template.get('show_cashier_name'):
        lines.append(f"{'Cashier':<{label_width}}: {bill_data.get('cashier', '-')}")
    
    if template.get('show_customer_name') and bill_data.get('customer_name'):
        lines.append(f"{'Customer':<{label_width}}: {bill_data['customer_name']}")
    
    if template.get('show_table_number') and bill_data.get('table_number'):
        lines.append(f"{'Table':<{label_width}}: {bill_data['table_number']}")
    
    lines.append(separator())
    
    # Items
    currency_symbol = 'Rp ' if template.get('show_currency_symbol') else ''
    
    for item in bill_data.get('items', []):
        # Item name
        item_name = item.get('name', '')
        if template.get('show_item_code') and item.get('code'):
            item_name = f"[{item['code']}] {item_name}"
        
        lines.append(item_name[:paper_width])
        
        # Quantity x Price = Total
        qty = item.get('quantity', 1)
        price = item.get('price', 0)
        total = qty * price
        
        if template.get('price_alignment') == 'right':
            qty_price = f"{qty} x {currency_symbol}{price:,.0f}"
            total_text = f"{currency_symbol}{total:,.0f}"
            lines.append(left_right_text(f"  {qty_price}", total_text))
        else:
            lines.append(f"  {qty} x {currency_symbol}{price:,.0f} = {currency_symbol}{total:,.0f}")
        
        # Modifiers
        if template.get('show_modifiers') and item.get('modifiers'):
            for mod in item['modifiers']:
                lines.append(f"    + {mod['name']}")
        
        # Category
        if template.get('show_item_category') and item.get('category'):
            lines.append(f"    ({item['category']})")
    
    lines.append(separator())
    
    # Totals
    if template.get('show_subtotal'):
        subtotal = bill_data.get('subtotal', 0)
        lines.append(left_right_text('Subtotal:', f"{currency_symbol}{subtotal:,.0f}"))
    
    if template.get('show_tax') and bill_data.get('tax', 0) > 0:
        tax = bill_data.get('tax', 0)
        lines.append(left_right_text('Tax:', f"{currency_symbol}{tax:,.0f}"))
    
    if template.get('show_service_charge') and bill_data.get('service_charge', 0) > 0:
        service = bill_data.get('service_charge', 0)
        lines.append(left_right_text('Service:', f"{currency_symbol}{service:,.0f}"))
    
    if template.get('show_discount') and bill_data.get('discount', 0) > 0:
        discount = bill_data.get('discount', 0)
        lines.append(left_right_text('Discount:', f"-{currency_symbol}{discount:,.0f}"))
    
    # Grand Total (always show)
    total = bill_data.get('total', 0)
    lines.append('')
    lines.append(left_right_text('TOTAL:', f"{currency_symbol}{total:,.0f}"))
    lines.append('')
    
    # Payment info
    if template.get('show_payment_method') and bill_data.get('payment_method'):
        lines.append(f"Payment: {bill_data['payment_method']}")
    
    if template.get('show_paid_amount') and bill_data.get('paid_amount'):
        paid = bill_data.get('paid_amount', 0)
        lines.append(left_right_text('Paid:', f"{currency_symbol}{paid:,.0f}"))
    
    if template.get('show_change') and bill_data.get('change', 0) > 0:
        change = bill_data.get('change', 0)
        lines.append(left_right_text('Change:', f"{currency_symbol}{change:,.0f}"))
    
    lines.append(separator())
    
    # Footer
    if template.get('footer_line_1'):
        lines.append(center_text(template['footer_line_1']))
    if template.get('footer_line_2'):
        lines.append(center_text(template['footer_line_2']))
    if template.get('footer_line_3'):
        lines.append(center_text(template['footer_line_3']))
    
    # QR code placeholder
    if template.get('show_qr_payment') and bill_data.get('qr_code'):
        lines.append('')
        lines.append(center_text('[QR CODE]'))
        lines.append(center_text(bill_data.get('qr_code', '')))
    
    # Feed lines
    feed_lines = template.get('feed_lines', 3)
    lines.extend([''] * feed_lines)
    
    return '\n'.join(lines)


@app.route('/api/print/receipt', methods=['POST'])
def api_print_receipt():
    """Print receipt with template from database"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Get connection config (use cwd for PyInstaller bundle compatibility)
        config_path = Path(os.getcwd()) / 'config.json'
        edge_server = 'http://127.0.0.1:8001'
        terminal_code = None
        company_code = None
        brand_code = None
        store_code = None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                json_config = json.load(f)
                edge_server = json_config.get('edge_server', edge_server)
                terminal_code = json_config.get('terminal_code')
                company_code = json_config.get('company_code')
                brand_code = json_config.get('brand_code')
                store_code = json_config.get('store_code')
        except Exception as e:
            print(f"[Print Receipt] Warning: Could not load config.json: {e}")
        
        # Fetch terminal config to get print_to setting
        print_to_destination = 'printer'  # default
        
        try:
            import requests
            params = {'terminal_code': terminal_code}
            if company_code:
                params['company_code'] = company_code
            if brand_code:
                params['brand_code'] = brand_code
            if store_code:
                params['store_code'] = store_code
            
            response = requests.get(f"{edge_server}/api/terminal/config", params=params, timeout=5)
            if response.status_code == 200:
                config_data = response.json()
                if config_data.get('success'):
                    print_to_destination = config_data.get('terminal', {}).get('device_config', {}).get('print_to', 'printer')
        except Exception as e:
            print(f"[Print Receipt] Warning: Could not fetch terminal config: {e}")

        # Fetch receipt template
        template = fetch_receipt_template(edge_server, terminal_code, company_code, brand_code, store_code)
        
        if not template:
            return jsonify({
                'success': False, 
                'error': 'Receipt template not found'
            }), 404
        
        # Generate formatted receipt text
        receipt_text = format_receipt_text(data, template)
        
        # Download and process logo if available
        logo_data = b''
        if template.get('show_logo') and template.get('logo_url'):
            logo_url = template.get('logo_url')
            paper_width = template.get('paper_width', 58)
            logo_data = download_and_process_logo(logo_url, edge_server, paper_width)
        
        # Check print destination
        if print_to_destination == 'file':
            # Save to file instead (in same directory as POSLauncher.exe)
            from datetime import datetime
            
            # Use current working directory (where POSLauncher.exe is located)
            receipts_dir = Path(os.getcwd()) / 'receipts_output'
            
            # Get business date from bill data (format: DD/MM/YYYY -> YYYYMMDD)
            business_date_str = data.get('date', '')
            try:
                if business_date_str and '/' in business_date_str:
                    # Parse DD/MM/YYYY format
                    day, month, year = business_date_str.split('/')
                    business_date_folder = f"{year}{month}{day}"
                else:
                    # Fallback to current date if parsing fails
                    business_date_folder = datetime.now().strftime('%Y%m%d')
            except:
                business_date_folder = datetime.now().strftime('%Y%m%d')
            
            # Create date-based folder structure
            date_receipts_dir = receipts_dir / business_date_folder
            date_receipts_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%H%M%S')
            receipt_number = data.get('receipt_number', 'UNKNOWN')
            filename = f"receipt_{receipt_number}_{timestamp}.txt"
            filepath = date_receipts_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(receipt_text)
            
            print(f"[Print Receipt] SUCCESS - Saved to: {filepath}")
            return jsonify({
                'success': True,
                'print_to': 'file',
                'file_path': str(filepath),
                'business_date': business_date_folder,
                'template': template.get('template_name')
            }), 200
        else:
            # Print to printer
            # Get printer name from data or use default
            printer_name = data.get('printer_name')
            
            # Prepare print data
            print_data = {
                'type': 'receipt',
                'text': receipt_text,
                'logo_data': logo_data,
                'auto_cut': template.get('auto_cut', True),
                'printer_name': printer_name
            }
            
            # Print using existing function
            result = print_to_local_printer(print_data)
            
            if result['success']:
                print(f"[Print Receipt] SUCCESS - Printed to {result.get('printer', 'default printer')}")
                return jsonify({
                    'success': True,
                    'print_to': 'printer',
                    'printer': result.get('printer'),
                    'template': template.get('template_name')
                }), 200
            else:
                print(f"[Print Receipt] FAILED - {result.get('error')}")
                return jsonify(result), 500
    
    except Exception as e:
        print(f"[Print Receipt] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def run_server(host='127.0.0.1', port=5000):
    """Run Flask server"""
    print(f"[Local API] Starting on {host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == '__main__':
    run_server()
