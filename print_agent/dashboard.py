"""
Print Agent Dashboard - Web-based Monitoring & Maintenance
Access: http://localhost:5050
"""
import os
import sys
import json
import time
import subprocess
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from escpos.printer import Win32Raw

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Enable CORS for POS integration
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:8000", "http://127.0.0.1:8000", "http://172.17.46.56:8000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Load config
CONFIG_FILE = 'print_agent_config.json'
PRINTED_JOBS_FILE = 'printed_jobs.json'
LOG_FILE = 'print_agent.log'


def load_config():
    """Load print agent config"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def load_printed_jobs():
    """Load printed jobs history"""
    try:
        with open(PRINTED_JOBS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []


def get_printer_status():
    """Check printer health"""
    config = load_config()
    printer_name = config.get('printer', {}).get('name', 'TP808')
    
    try:
        printer = Win32Raw(printer_name)
        printer.close()
        return {
            'status': 'OK',
            'message': 'Printer tersedia dan siap',
            'color': 'success'
        }
    except FileNotFoundError:
        return {
            'status': 'USB_DISCONNECTED',
            'message': 'Printer tidak terhubung (USB terputus)',
            'color': 'danger'
        }
    except PermissionError:
        return {
            'status': 'OFFLINE',
            'message': 'Printer offline atau digunakan aplikasi lain',
            'color': 'warning'
        }
    except Exception as e:
        return {
            'status': 'ERROR',
            'message': f'Error: {str(e)}',
            'color': 'danger'
        }


def get_agent_status():
    """Check if agent is running"""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                # Check for both .py and .exe versions
                if cmdline and any('agent_v2.py' in str(cmd) or 'PrintAgent.exe' in str(cmd) for cmd in cmdline):
                    return {
                        'running': True,
                        'pid': proc.info['pid'],
                        'color': 'success'
                    }
            except:
                continue
        return {'running': False, 'pid': None, 'color': 'danger'}
    except:
        return {'running': False, 'pid': None, 'color': 'warning'}


def get_recent_logs(lines=50):
    """Get recent log entries"""
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return all_lines[-lines:]
    except:
        return []


@app.route('/')
def index():
    """Dashboard home"""
    return render_template('dashboard.html')


@app.route('/api/status')
def api_status():
    """Get system status"""
    config = load_config()
    printer_status = get_printer_status()
    agent_status = get_agent_status()
    printed_jobs = load_printed_jobs()
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'terminal_id': config.get('terminal_identity', {}).get('terminal_id', 'N/A'),
        'printer': {
            'name': config.get('printer', {}).get('name', 'N/A'),
            'brand': config.get('printer', {}).get('brand', 'N/A'),
            'status': printer_status['status'],
            'message': printer_status['message'],
            'color': printer_status['color']
        },
        'agent': {
            'running': agent_status['running'],
            'pid': agent_status['pid'],
            'color': agent_status['color']
        },
        'jobs': {
            'history_count': len(printed_jobs),
            'history_file': PRINTED_JOBS_FILE
        }
    })


@app.route('/api/logs')
def api_logs():
    """Get recent logs"""
    lines = request.args.get('lines', 50, type=int)
    logs = get_recent_logs(lines)
    return jsonify({'logs': logs})


@app.route('/api/test-print', methods=['POST'])
def api_test_print():
    """Test print"""
    config = load_config()
    printer_name = config.get('printer', {}).get('name', 'TP808')
    
    try:
        printer = Win32Raw(printer_name)
        
        # Print test receipt
        printer._raw(b'\x1b\x40')  # Initialize
        printer.set(align='center', bold=True)
        printer.text("TEST PRINT\n")
        printer.text("=============\n\n")
        printer.set(align='left', bold=False)
        printer.text(f"Terminal: {config.get('terminal_identity', {}).get('terminal_id', 'N/A')}\n")
        printer.text(f"Printer: {printer_name}\n")
        printer.text(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        printer.text("\n\n")
        printer.set(align='center')
        printer.text("Print Agent Dashboard\n")
        printer.text("Test Successful!\n")
        printer.text("\n\n\n")
        printer.cut()
        printer.close()
        
        return jsonify({
            'success': True,
            'message': 'Test print berhasil!'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Test print gagal: {str(e)}'
        }), 500


@app.route('/api/clear-history', methods=['POST'])
def api_clear_history():
    """Clear printed jobs history"""
    try:
        with open(PRINTED_JOBS_FILE, 'w') as f:
            json.dump([], f)
        
        return jsonify({
            'success': True,
            'message': 'History berhasil dihapus'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Gagal menghapus history: {str(e)}'
        }), 500


@app.route('/api/printer-info')
def api_printer_info():
    """Get detailed printer info"""
    config = load_config()
    printer_config = config.get('printer', {})
    
    return jsonify({
        'name': printer_config.get('name', 'N/A'),
        'brand': printer_config.get('brand', 'N/A'),
        'model': printer_config.get('model', 'N/A'),
        'paper_width': printer_config.get('paper_width', 32),
        'type': printer_config.get('type', 'win32')
    })


@app.route('/api/start-agent', methods=['POST'])
def api_start_agent():
    """Start print agent"""
    try:
        # Check if already running
        agent_status = get_agent_status()
        if agent_status['running']:
            return jsonify({
                'success': False,
                'message': f'Agent sudah running (PID: {agent_status["pid"]})'
            }), 400
        
        # Determine which agent to start
        # CREATE_NO_WINDOW = 0x08000000 for silent background execution
        CREATE_NO_WINDOW = 0x08000000
        
        # Check multiple locations for PrintAgent.exe
        # Priority: same folder (production) > dist folder (dev) > script directory
        current_dir = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.getcwd()
        
        agent_exe_paths = [
            'PrintAgent.exe',                                           # Current directory (when running from same folder)
            os.path.join(current_dir, 'PrintAgent.exe'),               # Same folder as dashboard exe (PRODUCTION)
            'dist/PrintAgent.exe',                                      # dist folder (development)
            os.path.join(os.path.dirname(__file__), 'PrintAgent.exe'), # Script directory
            os.path.join(os.path.dirname(__file__), 'dist', 'PrintAgent.exe')  # Script dir/dist
        ]
        
        agent_exe = None
        for path in agent_exe_paths:
            if os.path.exists(path):
                agent_exe = os.path.abspath(path)
                break
        
        if agent_exe:
            # Start executable version silently in background
            subprocess.Popen(
                [agent_exe],
                creationflags=CREATE_NO_WINDOW,
                cwd=os.path.dirname(agent_exe),  # Run from exe directory
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            agent_type = f'executable ({os.path.basename(agent_exe)})'
        elif os.path.exists('agent_v2.py'):
            # Start Python version silently in background
            subprocess.Popen(
                [sys.executable, 'agent_v2.py'],
                creationflags=CREATE_NO_WINDOW,
                cwd=os.getcwd(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            agent_type = 'python'
        else:
            return jsonify({
                'success': False,
                'message': 'Agent tidak ditemukan. Cek folder dist/ untuk PrintAgent.exe atau agent_v2.py di root'
            }), 404
        
        # Wait a bit and check if started
        time.sleep(2)
        agent_status = get_agent_status()
        
        if agent_status['running']:
            return jsonify({
                'success': True,
                'message': f'Agent berhasil distart ({agent_type}, PID: {agent_status["pid"]})'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Agent gagal start, periksa log untuk detail'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error starting agent: {str(e)}'
        }), 500


@app.route('/api/stop-agent', methods=['POST'])
def api_stop_agent():
    """Stop print agent"""
    try:
        import psutil
        
        agent_status = get_agent_status()
        if not agent_status['running']:
            return jsonify({
                'success': False,
                'message': 'Agent tidak sedang running'
            }), 400
        
        pid = agent_status['pid']
        
        # Kill the process
        try:
            proc = psutil.Process(pid)
            proc.terminate()  # Graceful shutdown
            
            # Wait up to 5 seconds for graceful shutdown
            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                # Force kill if not responding
                proc.kill()
            
            return jsonify({
                'success': True,
                'message': f'Agent berhasil distop (PID: {pid})'
            })
            
        except psutil.NoSuchProcess:
            return jsonify({
                'success': False,
                'message': f'Process PID {pid} tidak ditemukan'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error stopping agent: {str(e)}'
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("PRINT AGENT DASHBOARD")
    print("=" * 60)
    print(f"Access: http://localhost:5050")
    print(f"Ctrl+C to stop")
    print("=" * 60)
    
    # Create templates folder if not exists
    os.makedirs('templates', exist_ok=True)
    
    app.run(host='0.0.0.0', port=5050, debug=True)
