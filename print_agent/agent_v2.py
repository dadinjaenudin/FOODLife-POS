"""
Print Agent - Production Ready (Windows-First, Offline-First)
Senior POS & Printing System Architecture

Design Principles:
- Never double-print silently
- Fail loudly and clearly
- Offline-first with safe recovery
- Operational logging for support
- Printer-agnostic receipt engine
"""
import os
import sys
import time
import json
import logging
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

try:
    from escpos.printer import Win32Raw
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    print("[ERROR] Win32Raw not available - Windows printer support disabled")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[ERROR] requests not available - API mode disabled")


# ============================================================================
# PRINTER PROFILE SYSTEM
# ============================================================================

class PrinterProfile(ABC):
    """
    Abstract base class for printer-specific behavior
    
    Encapsulates ESC/POS command differences between printer brands.
    Each printer brand has different command support:
    - Epson/XPrinter: Full ESC/POS support
    - HRPT: ESC/POS-like but limited (no condensed font)
    - Generic: Safe fallback using basic commands
    """
    
    @abstractmethod
    def init_printer(self, printer):
        """Initialize printer, clear all settings"""
        pass
    
    @abstractmethod
    def set_small_font(self, printer):
        """Set small/normal font for receipt body"""
        pass
    
    @abstractmethod
    def set_big_font(self, printer):
        """Set big font for queue numbers"""
        pass
    
    @abstractmethod
    def reset_font(self, printer):
        """Reset to default font"""
        pass
    
    def get_paper_width(self):
        """Return paper width in characters (default 32 for 58mm)"""
        return 32


class EpsonProfile(PrinterProfile):
    """
    Epson TM-series and XPrinter (Full ESC/POS support)
    
    Features:
    - ESC ! 0x01: Condensed font (small, efficient)
    - ESC ! 0x30: Double-size font
    - GS ! 0x11: 2x width + height
    - Full command set support
    """
    
    def init_printer(self, printer):
        """ESC @ - Initialize printer (clear all settings)"""
        printer._raw(b'\x1b\x40')
    
    def set_small_font(self, printer):
        """ESC ! 0x01 - Condensed/compressed font"""
        printer._raw(b'\x1b\x21\x01')
    
    def set_big_font(self, printer):
        """GS ! 0x11 - 2x width + 2x height"""
        printer._raw(b'\x1d\x21\x11')
    
    def reset_font(self, printer):
        """ESC ! 0x00 - Reset to normal font"""
        printer._raw(b'\x1b\x21\x00')


class HRPTProfile(PrinterProfile):
    """
    HRPT TP808 and similar Chinese thermal printers
    
    Limitations:
    - ESC ! commands (0x01 condensed) NOT supported
    - GS ! commands ARE supported
    - ESC @ (initialize) is critical for reset
    
    Strategy: Use Font A baseline + GS ! for sizing
    """
    
    def init_printer(self, printer):
        """ESC @ - CRITICAL for HRPT (clears all formatting)"""
        printer._raw(b'\x1b\x40')
    
    def set_small_font(self, printer):
        """
        HRPT cannot do condensed font
        Use ESC @ reset + Font A baseline instead
        """
        printer._raw(b'\x1b\x40')  # Reset everything
        printer.set(
            font='a',
            width=1,
            height=1,
            bold=False,
            underline=False,
            align='left'
        )
    
    def set_big_font(self, printer):
        """GS ! 0x11 - This DOES work on HRPT"""
        printer._raw(b'\x1d\x21\x11')
    
    def reset_font(self, printer):
        """GS ! 0x00 - Reset character size"""
        printer._raw(b'\x1d\x21\x00')


class GenericProfile(PrinterProfile):
    """
    Generic/Unknown printer fallback
    
    Uses only safe, universal commands:
    - No RAW ESC/POS bytes
    - python-escpos high-level API only
    - Maximum compatibility
    """
    
    def init_printer(self, printer):
        """Safe initialization"""
        try:
            printer._raw(b'\x1b\x40')
        except:
            pass  # Printer might not support it
    
    def set_small_font(self, printer):
        """Safe small font using API"""
        printer.set(
            font='a',
            width=1,
            height=1,
            bold=False,
            underline=False,
            align='left'
        )
    
    def set_big_font(self, printer):
        """Safe big font using API"""
        printer.set(
            width=2,
            height=2,
            bold=True
        )
    
    def reset_font(self, printer):
        """Safe reset using API"""
        printer.set(
            width=1,
            height=1,
            bold=False
        )


def get_printer_profile(config) -> PrinterProfile:
    """
    Factory function: Pick appropriate printer profile
    
    Args:
        config: Print agent config dict with 'printer_brand' key
    
    Returns:
        PrinterProfile instance for the specified brand
    """
    printer_config = config.get('printer', {})
    brand = printer_config.get('brand', '').upper()
    
    profile_map = {
        'EPSON': EpsonProfile,
        'XPRINTER': EpsonProfile,  # XPrinter uses same commands as Epson
        'HRPT': HRPTProfile,
        'GENERIC': GenericProfile
    }
    
    profile_class = profile_map.get(brand, GenericProfile)
    return profile_class()


class PrinterStatus(Enum):
    """Printer health status"""
    OK = "OK"
    PAPER_OUT = "PAPER_OUT"
    COVER_OPEN = "COVER_OPEN"
    OFFLINE = "PRINTER_OFFLINE"
    USB_DISCONNECTED = "USB_DISCONNECTED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class JobStatus(Enum):
    """Print job lifecycle"""
    PENDING = "pending"
    FETCHED = "fetched"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"


class PrintAgentV2:
    """
    Production-Ready Print Agent
    Windows-First, Offline-First, Support-Friendly
    """
    
    def __init__(self, config_file='print_agent_config.json'):
        """Initialize agent with config"""
        self.config = self.load_config(config_file)
        self.setup_logging()
        
        # Terminal identity
        identity = self.config['terminal_identity']
        self.terminal_id = identity['terminal_id']
        self.printer_role = identity['printer_role']
        self.location_id = identity['location_id']
        
        # Server config
        server = self.config['server']
        self.server_url = server['url']
        self.api_key = server['api_key']
        self.poll_interval = server['poll_interval']
        self.heartbeat_interval = server['heartbeat_interval']
        
        # Job types this agent accepts
        self.job_types_accepted = self.config['job_types_accepted']
        
        # Printer profile (brand-specific behavior)
        self.printer_profile = get_printer_profile(self.config)
        printer_config = self.config.get('printer', {})
        self.printer_brand = printer_config.get('brand', 'GENERIC').upper()
        self.paper_width = printer_config.get('paper_width', 32)
        
        # Error handling config
        error_config = self.config.get('error_handling', {})
        self.max_retry = error_config.get('max_retry', 3)
        self.backoff_seconds = error_config.get('backoff_seconds', [5, 10, 30])
        
        # State
        self.printer = None
        self.printer_status = PrinterStatus.UNKNOWN_ERROR
        self.running = False
        self.is_online = False
        self.last_heartbeat = None
        self.last_job_id = None
        self.consecutive_errors = 0
        
        # Persistent job tracking (critical for idempotent guarantee)
        self.printed_jobs_file = 'printed_jobs.json'
        self.printed_jobs = self.load_printed_jobs()
        
        self.logger.info("=" * 60)
        self.logger.info("PRINT AGENT V2 - PRODUCTION READY")
        self.logger.info("=" * 60)
        self.logger.info(f"Terminal ID: {self.terminal_id}")
        self.logger.info(f"Role: {self.printer_role}")
        self.logger.info(f"Location: {self.location_id}")
        self.logger.info(f"Printer Brand: {self.printer_brand}")
        self.logger.info(f"Paper Width: {self.paper_width} chars")
        self.logger.info(f"Accepted Jobs: {', '.join(self.job_types_accepted)}")
        self.logger.info("=" * 60)
    
    def load_config(self, config_file):
        """Load and validate configuration"""
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Validate required keys
        required = ['terminal_identity', 'server', 'printer', 'job_types_accepted']
        for key in required:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")
        
        return config
    
    def load_printed_jobs(self):
        """
        Load printed job UUIDs from persistent storage
        Returns: set of job_uuid strings
        
        Purpose: Prevent double-printing across agent restarts
        Design: Ring buffer (keep last 500 jobs only)
        """
        try:
            if os.path.exists(self.printed_jobs_file):
                with open(self.printed_jobs_file, 'r') as f:
                    jobs = json.load(f)
                    # Keep as set for O(1) lookup
                    return set(jobs)
            return set()
        except Exception as e:
            self.logger.warning(f"Failed to load printed jobs: {e}")
            return set()
    
    def save_printed_job(self, job_uuid):
        """
        Save job UUID to persistent storage (ring buffer)
        
        Ring buffer: Keep last 500 jobs only to prevent file bloat
        Average receipt: 5-10 per hour = 50-100 per day
        500 jobs = ~5-10 days of history
        """
        try:
            self.printed_jobs.add(job_uuid)
            
            # Ring buffer: keep last 500 only
            jobs_list = list(self.printed_jobs)[-500:]
            
            with open(self.printed_jobs_file, 'w') as f:
                json.dump(jobs_list, f)
            
            # Update memory set to match file
            self.printed_jobs = set(jobs_list)
            
        except Exception as e:
            self.logger.warning(f"Failed to save printed job: {e}")
    
    def setup_logging(self):
        """Setup structured logging for support"""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_file = log_config.get('log_file', 'print_agent.log')
        
        # Create logger
        self.logger = logging.getLogger('PrintAgent')
        self.logger.setLevel(log_level)
        
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(log_level)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        
        # Formatter - structured for support
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def check_printer_health(self):
        """
        Check printer status - Windows production reality
        Returns: PrinterStatus
        """
        try:
            if not HAS_WIN32:
                return PrinterStatus.OFFLINE
            
            printer_config = self.config['printer']
            printer_name = printer_config['name']
            
            # Try to init printer
            test_printer = Win32Raw(printer_name)
            test_printer.close()
            
            return PrinterStatus.OK
            
        except FileNotFoundError:
            return PrinterStatus.USB_DISCONNECTED
        except PermissionError:
            return PrinterStatus.OFFLINE
        except Exception as e:
            self.logger.error(f"Printer health check failed: {e}")
            return PrinterStatus.UNKNOWN_ERROR
    
    def get_printer(self):
        """
        Get printer instance with health check
        Operational failures: paper out, printer hang, driver issues
        """
        if self.printer:
            return self.printer
        
        try:
            self.printer_status = self.check_printer_health()
            
            if self.printer_status != PrinterStatus.OK:
                self.logger.warning(f"Printer not healthy: {self.printer_status.value}")
                return None
            
            printer_config = self.config['printer']
            printer_name = printer_config['name']
            
            self.printer = Win32Raw(printer_name)
            self.logger.info(f"[OK] Printer connected: {printer_name}")
            return self.printer
            
        except Exception as e:
            self.logger.error(f"Failed to get printer: {e}")
            self.printer_status = PrinterStatus.OFFLINE
            return None
    
    def send_heartbeat(self):
        """
        Send heartbeat to server
        Purpose: Detect dead agents, trigger alerts, enable rerouting
        """
        if not HAS_REQUESTS or not self.is_online:
            return
        
        try:
            heartbeat_data = {
                'terminal_id': self.terminal_id,
                'printer_role': self.printer_role,
                'location_id': self.location_id,
                'printer_status': self.printer_status.value,
                'agent_status': 'READY' if self.running else 'STOPPED',
                'last_job_id': self.last_job_id,
                'consecutive_errors': self.consecutive_errors,
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.post(
                f"{self.server_url}/api/print/heartbeat/",
                json=heartbeat_data,
                headers={'X-API-Key': self.api_key},
                timeout=5
            )
            
            if response.status_code == 200:
                self.last_heartbeat = datetime.now()
                self.logger.debug("[HEARTBEAT] Sent")
            else:
                self.logger.warning(f"Heartbeat failed: {response.status_code}")
                
        except Exception as e:
            self.logger.debug(f"Heartbeat error: {e}")
    
    def start(self):
        """Start print agent"""
        self.running = True
        self.logger.info("[OK] Print Agent V2 is running...")
        self.logger.info("Press Ctrl+C to stop\n")
        
        # Initial printer check
        printer = self.get_printer()
        if not printer:
            self.logger.error("[ERROR] Printer not available at startup")
            return
        
        # Main loop
        heartbeat_counter = 0
        
        try:
            while self.running:
                # Send heartbeat periodically
                if heartbeat_counter >= self.heartbeat_interval:
                    self.send_heartbeat()
                    heartbeat_counter = 0
                
                # Fetch and process jobs
                self.fetch_and_process_jobs()
                
                time.sleep(self.poll_interval)
                heartbeat_counter += self.poll_interval
                
        except KeyboardInterrupt:
            self.logger.info("\n[STOP] Stopping Print Agent...")
            self.running = False
        
        self.logger.info("[OK] Print Agent stopped")
    
    def fetch_and_process_jobs(self):
        """
        Fetch jobs from server and process them
        Idempotent: Uses job_uuid to prevent double-printing
        """
        if not HAS_REQUESTS:
            self.logger.warning("[ERROR] requests library not available")
            return
        
        try:
            # Fetch jobs for this terminal
            url = f"{self.server_url}/api/print/jobs/"
            params = {
                'terminal_id': self.terminal_id,
                'status': JobStatus.PENDING.value
            }
            
            self.logger.debug(f"[FETCH] Polling {url} with terminal_id={self.terminal_id}")
            
            response = requests.get(
                url,
                params=params,
                headers={'X-API-Key': self.api_key},
                timeout=5
            )
            
            self.logger.debug(f"[FETCH] Response status: {response.status_code}")
            
            if response.status_code != 200:
                if self.is_online:
                    self.logger.warning(f"[ERROR] API returned {response.status_code}: {response.text}")
                    self.is_online = False
                return
            
            if not self.is_online:
                self.logger.info("[ONLINE] Server connection restored")
            self.is_online = True
            
            jobs = response.json()
            self.logger.debug(f"[FETCH] Received {len(jobs) if isinstance(jobs, list) else 0} jobs")
            
            if not jobs:
                return
            
            self.logger.info(f"[JOBS] Found {len(jobs)} pending job(s)")
            
            # Process each job
            for job in jobs:
                self.process_job(job)
                
        except requests.exceptions.ConnectionError as e:
            if self.is_online:
                self.logger.warning(f"[OFFLINE] Server connection lost: {e}")
            self.is_online = False
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to fetch jobs: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def process_job(self, job):
        """
        Process a single print job with PERSISTENT idempotent guarantee
        
        Job lifecycle:
        1. PENDING (in database)
        2. FETCHED (agent picked it up)
        3. PRINTING (being sent to printer)
        4. COMPLETED (printed successfully)
        5. FAILED (error occurred, will retry)
        
        Idempotent guarantee:
        - Check printed_jobs.json (persistent across restarts)
        - Check last_job_id (in-memory for current session)
        """
        job_id = job.get('id')
        job_uuid = job.get('job_uuid')
        job_type = job.get('job_type')
        
        # CRITICAL: Prevent double-printing (persistent check)
        if job_uuid in self.printed_jobs:
            self.logger.debug(f"[SKIP] Job {job_id} already printed (found in history)")
            return
        
        # Additional in-memory check
        if self.last_job_id == job_uuid:
            self.logger.debug(f"[SKIP] Job {job_id} already processed (recent)")
            return
        
        self.logger.info(f"[JOB {job_id}] Processing: {job_type}")
        
        # Check if job type is accepted by this agent
        if job_type not in self.job_types_accepted:
            self.logger.warning(f"[JOB {job_id}] Job type '{job_type}' not accepted by this agent")
            return
        
        # Mark as fetched
        self.update_job_status(job_id, JobStatus.FETCHED)
        
        # Get printer
        printer = self.get_printer()
        if not printer:
            self.mark_job_failed(job_id, "PRINTER_OFFLINE")
            return
        
        # Mark as printing
        self.update_job_status(job_id, JobStatus.PRINTING)
        
        # RETRY LOGIC: Simple but effective
        success = False
        last_error = None
        
        for attempt in range(self.max_retry):
            try:
                if attempt > 0:
                    backoff = self.backoff_seconds[min(attempt - 1, len(self.backoff_seconds) - 1)]
                    self.logger.info(f"[JOB {job_id}] Retry {attempt}/{self.max_retry - 1} after {backoff}s...")
                    time.sleep(backoff)
                    
                    # Re-check printer health on retry
                    printer = self.get_printer()
                    if not printer:
                        self.logger.warning(f"[JOB {job_id}] Printer still unavailable")
                        continue
                
                # Try to print
                self.print_job(printer, job)
                
                # FORCE FLUSH: Close printer to ensure buffer is flushed
                if printer:
                    try:
                        printer.close()
                        self.logger.debug(f"[JOB {job_id}] Printer closed to flush buffer")
                    except:
                        pass
                    self.printer = None
                
                # Success!
                success = True
                break
                
            except Exception as e:
                last_error = e
                error_code = self.classify_error(e)
                self.logger.warning(f"[JOB {job_id}] Attempt {attempt + 1} failed: {error_code} - {e}")
                
                # Close printer on error
                if printer:
                    try:
                        printer.close()
                    except:
                        pass
                    self.printer = None
        
        # Final outcome
        if success:
            # Mark as completed
            self.update_job_status(job_id, JobStatus.COMPLETED)
            self.logger.info(f"[JOB {job_id}] [OK] Printed successfully")
            
            # PERSISTENT: Save to printed_jobs.json
            self.save_printed_job(job_uuid)
            
            # Remember last job (in-memory)
            self.last_job_id = job_uuid
            self.consecutive_errors = 0
        else:
            # All retries failed
            error_code = self.classify_error(last_error)
            self.mark_job_failed(job_id, error_code)
            self.logger.error(f"[JOB {job_id}] [FAILED] All {self.max_retry} attempts failed")
            self.consecutive_errors += 1
    
    def print_job(self, printer, job):
        """
        Execute the actual print operation
        Abstracted for different job types
        """
        job_type = job.get('job_type')
        
        if job_type == 'receipt':
            self.print_receipt(printer, job)
        elif job_type == 'reprint':
            self.print_receipt(printer, job)
        else:
            raise ValueError(f"Unknown job type: {job_type}")
    
    def print_receipt(self, printer, job):
        """
        Print receipt - PRINTER-AGNOSTIC
        
        Uses PrinterProfile system to abstract brand differences.
        This method is CLEAN and focuses on layout logic only.
        All ESC/POS command details are in the profile.
        """
        receipt_data = job.get('receipt_data', {})
        profile = self.printer_profile
        
        # Initialize printer
        profile.init_printer(printer)
        
        # ===== HEADER =====
        profile.set_small_font(printer)
        printer.set(align='center', bold=True)
        printer.text(f"{receipt_data.get('store_name', 'STORE')}\n")
        
        printer.set(bold=False)
        printer.text(f"{receipt_data.get('address', '')}\n")
        printer.text(f"Tel: {receipt_data.get('phone', '')}\n")
        printer.text("-" * self.paper_width + "\n")
        
        # ===== QUEUE NUMBER (BIG) =====
        queue_number = receipt_data.get('queue_number')
        if queue_number:
            profile.set_big_font(printer)
            printer.set(align='center', bold=True)
            printer.text("NOMOR ANTRIAN\n")
            printer.text(f"{queue_number}\n")
            
            # RESET TO NORMAL
            profile.reset_font(printer)
            profile.set_small_font(printer)
            printer.text("\n")
        
        # ===== BILL INFO =====
        printer.set(align='left')
        printer.text(f"No      : {receipt_data.get('bill_number', '')}\n")
        printer.text(f"Tanggal : {receipt_data.get('date', '')}\n")
        printer.text(f"Kasir   : {receipt_data.get('cashier', '')}\n")
        printer.text("-" * self.paper_width + "\n")
        
        # ===== ITEMS =====
        for item in receipt_data.get('items', []):
            # Truncate item name to paper width
            printer.text(item['name'][:self.paper_width] + "\n")
            printer.text(f"{item['qty']:>3} x {item['price']:>10} {item['subtotal']:>10}\n")
        
        printer.text("-" * self.paper_width + "\n")
        
        # ===== TOTAL =====
        printer.set(bold=True)
        total_value = receipt_data.get('total', 0)
        printer.text(f"TOTAL{'':>8}{total_value:>10}\n")
        printer.set(bold=False)
        
        # ===== FOOTER =====
        printer.text("\n")
        printer.set(align='center')
        printer.text("Terima kasih\n")
        printer.text("\n\n\n")
        
        # ===== CUT =====
        printer.cut()
    
    def update_job_status(self, job_id, status):
        """Update job status on server"""
        if not HAS_REQUESTS or not self.is_online:
            return
        
        try:
            requests.post(
                f"{self.server_url}/api/print/jobs/{job_id}/status/",
                json={'status': status.value},
                headers={'X-API-Key': self.api_key},
                timeout=5
            )
        except Exception as e:
            self.logger.debug(f"Failed to update job status: {e}")
    
    def mark_job_failed(self, job_id, error_code):
        """Mark job as failed with error code"""
        if not HAS_REQUESTS or not self.is_online:
            return
        
        try:
            requests.post(
                f"{self.server_url}/api/print/jobs/{job_id}/failed/",
                json={
                    'status': JobStatus.FAILED.value,
                    'error_code': error_code
                },
                headers={'X-API-Key': self.api_key},
                timeout=5
            )
        except Exception as e:
            self.logger.debug(f"Failed to mark job as failed: {e}")
    
    def classify_error(self, error):
        """
        Classify error into specific error codes for support
        Windows printer errors are... creative
        """
        error_str = str(error).lower()
        
        if 'filenotfounderror' in str(type(error).__name__).lower():
            return "USB_DISCONNECTED"
        elif 'permission' in error_str:
            return "PRINTER_OFFLINE"
        elif 'paper' in error_str:
            return "PAPER_OUT"
        elif 'cover' in error_str or 'open' in error_str:
            return "COVER_OPEN"
        else:
            return "UNKNOWN_ERROR"


def main():
    """Entry point"""
    try:
        agent = PrintAgentV2()
        agent.start()
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
