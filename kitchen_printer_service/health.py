"""
Health check HTTP endpoint
Exposes service status on port 9100
"""
from flask import Flask, jsonify
import logging
import threading
import time
from datetime import datetime

from database import get_service_stats

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Service metrics
service_start_time = datetime.now()
total_tickets_processed = 0
total_tickets_failed = 0
last_poll_time = None
db_connection = None


def set_db_connection(conn):
    """Set database connection for health checks"""
    global db_connection
    db_connection = conn


def increment_processed():
    """Increment processed counter"""
    global total_tickets_processed
    total_tickets_processed += 1


def increment_failed():
    """Increment failed counter"""
    global total_tickets_failed
    total_tickets_failed += 1


def update_last_poll():
    """Update last poll timestamp"""
    global last_poll_time
    last_poll_time = datetime.now()


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    Returns service status and basic metrics
    """
    uptime_seconds = int((datetime.now() - service_start_time).total_seconds())
    
    # Test database connection
    db_status = "unknown"
    try:
        if db_connection and db_connection.test_connection():
            db_status = "connected"
        else:
            db_status = "disconnected"
    except:
        db_status = "error"
    
    # Get stats from database
    stats = {}
    if db_status == "connected":
        try:
            stats = get_service_stats(db_connection.conn)
        except:
            pass
    
    # Calculate success rate
    total = total_tickets_processed + total_tickets_failed
    success_rate = 0.0
    if total > 0:
        success_rate = round((total_tickets_processed / total) * 100, 2)
    
    response = {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "Kitchen Printer Service",
        "version": "1.0.0",
        "uptime_seconds": uptime_seconds,
        "uptime_formatted": format_uptime(uptime_seconds),
        "database": db_status,
        "last_poll": last_poll_time.isoformat() if last_poll_time else None,
        "metrics": {
            "tickets_processed": total_tickets_processed,
            "tickets_failed": total_tickets_failed,
            "success_rate": success_rate,
            "pending_tickets": stats.get('pending_tickets', 0),
            "printed_today": stats.get('printed_today', 0),
            "failed_tickets": stats.get('failed_tickets', 0)
        }
    }
    
    return jsonify(response), 200 if db_status == "connected" else 503


@app.route('/metrics', methods=['GET'])
def metrics():
    """
    Metrics endpoint
    Returns detailed service metrics
    """
    uptime_seconds = int((datetime.now() - service_start_time).total_seconds())
    total = total_tickets_processed + total_tickets_failed
    success_rate = 0.0
    if total > 0:
        success_rate = round((total_tickets_processed / total) * 100, 2)
    
    response = {
        "uptime_seconds": uptime_seconds,
        "total_processed": total_tickets_processed,
        "total_failed": total_tickets_failed,
        "success_rate": success_rate,
        "last_poll_time": last_poll_time.isoformat() if last_poll_time else None
    }
    
    return jsonify(response), 200


@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping endpoint"""
    return jsonify({"status": "ok", "service": "kitchen_printer_service"}), 200


def format_uptime(seconds: int) -> str:
    """Format uptime seconds into human readable string"""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def run_health_server(port: int):
    """Run Flask health check server in background thread"""
    logger.info(f"Starting health check server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


def start_health_server(port: int):
    """Start health check server in separate thread"""
    thread = threading.Thread(target=run_health_server, args=(port,), daemon=True)
    thread.start()
    logger.info(f"✓ Health check server started on http://0.0.0.0:{port}/health")
