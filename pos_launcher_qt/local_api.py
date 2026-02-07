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
    """Load customer display configuration"""
    config_path = Path(__file__).parent / 'customer_display_config.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[Config] Error loading display config: {e}")
        return {
            'brand': {'name': 'POS System', 'logo_url': None},
            'slideshow': [],
            'running_text': 'Welcome!',
            'theme': {}
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
    
    receipt = INIT
    
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
def serve_customer_display():
    """Serve customer display HTML"""
    try:
        html_path = Path(__file__).parent / 'customer_display.html'
        print(f"[DEBUG] Serving HTML from: {html_path}")
        print(f"[DEBUG] File exists: {html_path.exists()}")
        
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
    config = load_display_config()
    return jsonify(config)


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


def run_server(host='127.0.0.1', port=5000):
    """Run Flask server"""
    print(f"[Local API] Starting on {host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == '__main__':
    run_server()
