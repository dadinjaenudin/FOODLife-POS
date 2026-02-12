"""
Kitchen Printer Agent - Production Ready
Autonomous agent untuk kitchen ticket printing

Design Principles:
- Database polling untuk new tickets
- Support Windows & Linux printers
- Network printer (RAW ESC/POS) & USB (Win32Raw)
- Offline-first dengan retry logic
- Dapat di-compile jadi standalone executable
"""
import os
import sys
import time
import json
import logging
import socket
import threading
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from http.server import HTTPServer, BaseHTTPRequestHandler

# Optional imports dengan fallback
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False
    print("[WARNING] python-dotenv not available - .env file support disabled")

try:
    from escpos.printer import Win32Raw, Network
    HAS_ESCPOS = True
except ImportError:
    HAS_ESCPOS = False
    print("[WARNING] python-escpos not available - Printer support limited")

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    print("[ERROR] psycopg2 not available - Cannot connect to database")
    sys.exit(1)


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Load configuration from JSON file and .env"""
    
    def __init__(self, config_file='kitchen_agent_config.json', env_file='.env'):
        # Get script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Make paths absolute relative to script location
        if not os.path.isabs(config_file):
            config_file = os.path.join(script_dir, config_file)
        if not os.path.isabs(env_file):
            env_file = os.path.join(script_dir, env_file)
        
        # Load .env file first (if available)
        if HAS_DOTENV and os.path.exists(env_file):
            load_dotenv(env_file)
            print(f"[INFO] Loaded environment from: {env_file}")
        
        self.config_file = config_file
        self.config = self.load_config()
        
        # Override with environment variables
        self.apply_env_overrides()
    
    def load_config(self):
        """Load and validate configuration"""
        if not os.path.exists(self.config_file):
            print(f"[ERROR] Config file not found: {self.config_file}")
            print("[INFO] Creating default config...")
            self.create_default_config()
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return config
    
    def apply_env_overrides(self):
        """Override config with environment variables"""
        # Database overrides
        if os.getenv('DB_HOST'):
            self.config['database']['host'] = os.getenv('DB_HOST')
        if os.getenv('DB_PORT'):
            self.config['database']['port'] = int(os.getenv('DB_PORT'))
        if os.getenv('DB_NAME'):
            self.config['database']['database'] = os.getenv('DB_NAME')
        if os.getenv('DB_USER'):
            self.config['database']['user'] = os.getenv('DB_USER')
        if os.getenv('DB_PASSWORD'):
            self.config['database']['password'] = os.getenv('DB_PASSWORD')
        
        # Agent overrides
        if os.getenv('AGENT_NAME'):
            self.config['agent']['name'] = os.getenv('AGENT_NAME')
        if os.getenv('STATION_IDS'):
            # Parse comma-separated station IDs: "1,2,3" -> [1,2,3]
            station_ids = [int(sid.strip()) for sid in os.getenv('STATION_IDS').split(',')]
            self.config['agent']['station_ids'] = station_ids

        # Health server overrides
        if os.getenv('HEALTH_SERVER_PORT'):
            if 'health_server' not in self.config:
                self.config['health_server'] = {}
            self.config['health_server']['port'] = int(os.getenv('HEALTH_SERVER_PORT'))
    
    def create_default_config(self):
        """Create default configuration file"""
        default_config = {
            "_comment": "Kitchen Printer Agent Configuration",
            
            "agent": {
                "name": "Kitchen-Agent-1",
                "version": "1.0.0",
                "station_ids": [1, 2, 3],
                 "heartbeat_interval": 30,
                 "brand_ids": [],
            },
            
            "database": {
                "host": "localhost",
                "port": 5433,
                "database": "fnb_edge_db",
                "user": "postgres",
                "password": "postgres"
            },
            
            "polling": {
                "interval_seconds": 2,
                "max_tickets_per_poll": 10,
                "retry_failed_tickets": True
            },
            "health_check": {
                "interval_seconds": 60,
                "timeout_seconds": 5
            },

            "health_server": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 5001
            },

            "printer": {
                "_comment": "Printer config is fetched from database (kitchen_stationprinter table)",
                "default_timeout": 5,
                "fallback_brand": "HRPT"
            },
            
            "logging": {
                "level": "INFO",
                "log_file": "kitchen_agent.log",
                "max_size_mb": 10
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
        
        print(f"[INFO] Default config created: {self.config_file}")
        return default_config
    
    def get(self, *keys, default=None):
        """Get nested config value"""
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value


# ============================================================================
# PRINTER PROFILES
# ============================================================================

class PrinterProfile(ABC):
    """Abstract base class for printer-specific ESC/POS commands"""
    
    @abstractmethod
    def init_printer(self):
        """Initialize printer commands"""
        pass
    
    @abstractmethod
    def set_normal_font(self):
        """Normal font commands"""
        pass
    
    @abstractmethod
    def set_double_font(self):
        """Double size font commands"""
        pass
    
    @abstractmethod
    def set_center_align(self):
        """Center alignment commands"""
        pass
    
    @abstractmethod
    def set_left_align(self):
        """Left alignment commands"""
        pass
    
    @abstractmethod
    def feed_and_cut(self):
        """Feed paper and cut commands"""
        pass


class HRPTProfile(PrinterProfile):
    """HRPT TP808 Printer Profile"""
    
    def init_printer(self):
        return b'\x1b@'  # ESC @
    
    def set_normal_font(self):
        return b'\x1d!\x00'  # GS ! 0x00
    
    def set_double_font(self):
        return b'\x1d!\x11'  # GS ! 0x11 (2x width + height)
    
    def set_center_align(self):
        return b'\x1ba\x01'  # ESC a 1
    
    def set_left_align(self):
        return b'\x1ba\x00'  # ESC a 0
    
    def feed_and_cut(self):
        # Feed 3 lines, beep, cut
        return b'\n\n\n' + b'\x1bd\x03' + b'\x1bB\x02\x02' + b'\x1dV\x00'


class EpsonProfile(PrinterProfile):
    """Epson TM-series Printer Profile"""
    
    def init_printer(self):
        return b'\x1b@'
    
    def set_normal_font(self):
        return b'\x1b!\x00'  # ESC ! 0x00
    
    def set_double_font(self):
        return b'\x1b!\x30'  # ESC ! 0x30
    
    def set_center_align(self):
        return b'\x1ba\x01'
    
    def set_left_align(self):
        return b'\x1ba\x00'
    
    def feed_and_cut(self):
        return b'\n\n\n' + b'\x1dV\x00'


# ============================================================================
# PRINTER INTERFACE
# ============================================================================

class PrinterInterface:
    """Unified printer interface for Network and Win32 with dynamic config"""
    
    def __init__(self, config: Config):
        self.config = config
        self.default_timeout = config.get('printer', 'default_timeout', default=5)
        self.fallback_brand = config.get('printer', 'fallback_brand', default='HRPT')
        self.logger = logging.getLogger('PrinterInterface')
        
        # Cache printer profiles
        self.profiles = {
            'HRPT': HRPTProfile(),
            'EPSON': EpsonProfile(),
            'XPRINTER': EpsonProfile()  # XPrinter uses Epson commands
        }
    
    def print_ticket(self, ticket_data, printer_config, db=None):
        """Print kitchen ticket with dynamic printer config"""
        try:
            # Get printer profile
            brand = printer_config.get('brand', self.fallback_brand).upper()
            profile = self.profiles.get(brand, self.profiles['HRPT'])
            chars = printer_config.get('chars_per_line', 42)

            # Route to appropriate formatter based on ticket type
            if ticket_data.get('printer_target') == 'checker' and db:
                raw_data = self._format_checker_ticket(ticket_data, profile, chars, db)
            else:
                raw_data = self._format_ticket(ticket_data, profile, chars, db)

            # Print based on type
            printer_type = printer_config.get('type', 'network')

            if printer_type == 'network':
                return self._print_network(raw_data, printer_config)
            elif printer_type == 'win32':
                return self._print_win32(raw_data, printer_config)
            else:
                self.logger.error(f"Unknown printer type: {printer_type}")
                return False

        except Exception as e:
            self.logger.error(f"Print failed: {e}")
            return False

    def _format_ticket(self, ticket, profile, chars_per_line=42, db=None):
        """Format kitchen ticket with template from database"""
        data = bytearray()
        sep = b'=' * chars_per_line + b'\n'
        dash_sep = b'-' * chars_per_line + b'\n'

        # Fetch kitchen template from DB
        tmpl = db.fetch_kitchen_template(ticket.get('brand_id')) if db else None

        # Template values with fallback defaults
        header1 = (tmpl.get('header_line_1') if tmpl else None) or 'KITCHEN TICKET'
        header2 = (tmpl.get('header_line_2') if tmpl else None) or ''
        footer1 = (tmpl.get('footer_line_1') if tmpl else None) or ''
        footer2 = (tmpl.get('footer_line_2') if tmpl else None) or ''
        show_bill = tmpl.get('show_bill_number', True) if tmpl else True
        show_table = tmpl.get('show_table_number', True) if tmpl else True
        show_customer = tmpl.get('show_customer_name', True) if tmpl else True
        show_station = tmpl.get('show_station_name', True) if tmpl else True
        show_datetime = tmpl.get('show_date_time', True) if tmpl else True
        show_qty = tmpl.get('show_item_qty', True) if tmpl else True
        show_notes = tmpl.get('show_item_notes', True) if tmpl else True
        feed_lines = tmpl.get('feed_lines', 3) if tmpl else 3

        # Initialize
        data.extend(profile.init_printer())

        # Header - Center aligned, double size
        data.extend(profile.set_center_align())
        data.extend(profile.set_double_font())
        data.extend(header1.encode('utf-8') + b'\n')
        data.extend(profile.set_normal_font())
        if header2:
            data.extend(header2.encode('utf-8') + b'\n')
        data.extend(sep)

        # Ticket info - Left aligned
        data.extend(profile.set_left_align())
        if show_bill:
            data.extend(f"Bill     : {ticket['bill_number']}\n".encode('utf-8'))
        if show_table:
            data.extend(f"Table    : {ticket.get('table_number', 'N/A')}\n".encode('utf-8'))
        if show_customer and ticket.get('customer_name'):
            data.extend(f"Customer : {ticket['customer_name']}\n".encode('utf-8'))
        if show_station:
            data.extend(f"Station  : {ticket['printer_target'].upper()}\n".encode('utf-8'))
        if show_datetime:
            data.extend(f"Time     : {ticket['created_at']}\n".encode('utf-8'))

        data.extend(b'\n')
        data.extend(dash_sep)

        # Items
        for item in ticket['items']:
            qty = item['quantity']
            name = item['product_name']
            qty_str = f"{qty}x " if show_qty else ''
            data.extend(f"{qty_str}{name}\n".encode('utf-8'))

            if show_notes and item.get('notes'):
                data.extend(f"   Note: {item['notes']}\n".encode('utf-8'))

        # Footer
        data.extend(b'\n')
        data.extend(sep)
        data.extend(profile.set_center_align())
        if footer1:
            data.extend(footer1.encode('utf-8') + b'\n')
        elif not tmpl:
            # Default footer when no template
            data.extend(f"Printer: {ticket['printer_target']}\n".encode('utf-8'))
        if footer2:
            data.extend(footer2.encode('utf-8') + b'\n')

        # Feed and cut
        data.extend(b'\n' * feed_lines)
        data.extend(profile.feed_and_cut())

        return bytes(data)

    def _format_checker_ticket(self, ticket, profile, chars_per_line, db):
        """Format checker ticket with template from database"""
        data = bytearray()
        sep = b'=' * chars_per_line + b'\n'
        dash_sep = b'-' * chars_per_line + b'\n'

        # Fetch checker template from DB
        tmpl = db.fetch_checker_template(ticket.get('brand_id'))

        # Template defaults
        header1 = (tmpl.get('header_line_1') if tmpl else None) or 'CHECKER'
        header2 = (tmpl.get('header_line_2') if tmpl else None) or 'Cek item sebelum disajikan'
        footer1 = (tmpl.get('footer_line_1') if tmpl else None) or 'CEK SEMUA ITEM SEBELUM DISAJIKAN'
        footer2 = (tmpl.get('footer_line_2') if tmpl else None) or ''
        show_bill = tmpl.get('show_bill_number', True) if tmpl else True
        show_table = tmpl.get('show_table_number', True) if tmpl else True
        show_datetime = tmpl.get('show_date_time', True) if tmpl else True
        show_station = tmpl.get('show_station_label', True) if tmpl else True
        show_notes = tmpl.get('show_item_notes', True) if tmpl else True
        show_qty = tmpl.get('show_item_qty', True) if tmpl else True
        show_checkbox = tmpl.get('show_checkbox', True) if tmpl else True
        feed_lines = tmpl.get('feed_lines', 3) if tmpl else 3

        # Initialize
        data.extend(profile.init_printer())

        # Header
        data.extend(profile.set_center_align())
        data.extend(profile.set_double_font())
        data.extend(header1.encode('utf-8') + b'\n')
        data.extend(profile.set_normal_font())
        data.extend(header2.encode('utf-8') + b'\n')
        data.extend(sep)

        # Bill info
        data.extend(profile.set_left_align())
        if show_bill:
            data.extend(f"Bill     : {ticket['bill_number']}\n".encode('utf-8'))
        if show_table:
            data.extend(f"Table    : {ticket.get('table_number', 'N/A')}\n".encode('utf-8'))
        if show_datetime:
            data.extend(f"Time     : {ticket['created_at']}\n".encode('utf-8'))

        data.extend(b'\n')
        data.extend(dash_sep)
        data.extend(b'\n')

        # Items with checkboxes
        for item in ticket['items']:
            qty = item['quantity']
            name = item['product_name']
            notes = item.get('notes', '')
            station = item.get('station', '')

            # Build item line
            prefix = '[ ]  ' if show_checkbox else '  '
            qty_str = f"{qty}x " if show_qty else ''
            station_str = f" [{station.upper()}]" if (show_station and station) else ''
            data.extend(f"{prefix}{qty_str}{name}{station_str}\n".encode('utf-8'))

            # Notes
            if show_notes and notes:
                data.extend(f"     {notes}\n".encode('utf-8'))

            data.extend(b'\n')

        # Footer
        data.extend(dash_sep)
        data.extend(profile.set_center_align())
        data.extend(f"Total Items: {len(ticket['items'])}\n".encode('utf-8'))
        data.extend(sep)
        if footer1:
            data.extend(footer1.encode('utf-8') + b'\n')
        if footer2:
            data.extend(footer2.encode('utf-8') + b'\n')

        # Feed extra lines and cut
        data.extend(b'\n' * feed_lines)
        data.extend(profile.feed_and_cut())

        return bytes(data)
    
    def _print_network(self, data, printer_config):
        """Print via network socket (RAW)"""
        host = printer_config.get('host')
        port = printer_config.get('port', 9100)
        timeout = printer_config.get('timeout', self.default_timeout)
        
        self.logger.info(f"Printing to network: {host}:{port}")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.sendall(data)
            sock.close()
            
            self.logger.info("Print successful")
            return True
        
        except Exception as e:
            self.logger.error(f"Network print failed: {e}")
            return False
    
    def _print_win32(self, data, printer_config):
        """Print via Windows printer driver"""
        if not HAS_ESCPOS:
            self.logger.error("python-escpos not available")
            return False
        
        printer_name = printer_config.get('name')
        self.logger.info(f"Printing to Win32: {printer_name}")
        
        try:
            printer = Win32Raw(printer_name)
            printer._raw(data)
            printer.close()
            
            self.logger.info("Print successful")
            return True
        
        except Exception as e:
            self.logger.error(f"Win32 print failed: {e}")
            return False


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class DatabaseManager:
    """PostgreSQL database operations"""
    
    def __init__(self, config: Config):
        self.config = config
        self.conn = None
        self.logger = logging.getLogger('DatabaseManager')
        self.connect()
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            db_host = self.config.get('database', 'host')
            db_port = self.config.get('database', 'port')
            db_name = self.config.get('database', 'database')
            db_user = self.config.get('database', 'user')
            db_pass = self.config.get('database', 'password')
            
            print(f"[DEBUG] Connecting to database:")
            print(f"  Host: {db_host}")
            print(f"  Port: {db_port}")
            print(f"  Database: {db_name}")
            print(f"  User: {db_user}")
            print(f"  Password: {'*' * len(str(db_pass)) if db_pass else 'None'}")
            
            self.conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_pass
            )
            self.conn.autocommit = True
            self.logger.info("Database connected successfully")
        
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise
    
    def get_printer_for_station(self, station_code, brand_id=None):
        """Get printer configuration from database for station + brand.

        In multi-brand food courts, each brand has its own printer per station.
        brand_id ensures the ticket is routed to the correct brand's printer.
        """
        try:
            cursor = self.conn.cursor()

            if brand_id:
                # Multi-brand: match station + brand for correct printer routing
                query = """
                    SELECT
                        printer_name,
                        printer_ip,
                        printer_port,
                        is_active,
                        priority,
                        COALESCE(printer_brand, 'HRPT') as printer_brand,
                        COALESCE(printer_type, 'network') as printer_type,
                        COALESCE(timeout_seconds, 5) as timeout_seconds,
                        COALESCE(paper_width_mm, 80) as paper_width_mm,
                        COALESCE(chars_per_line, 42) as chars_per_line
                    FROM kitchen_stationprinter
                    WHERE station_code = %s AND brand_id = %s AND is_active = true
                    ORDER BY priority ASC
                    LIMIT 1
                """
                cursor.execute(query, (station_code, brand_id))
            else:
                # Fallback: single-brand or brand not set on ticket
                query = """
                    SELECT
                        printer_name,
                        printer_ip,
                        printer_port,
                        is_active,
                        priority,
                        COALESCE(printer_brand, 'HRPT') as printer_brand,
                        COALESCE(printer_type, 'network') as printer_type,
                        COALESCE(timeout_seconds, 5) as timeout_seconds,
                        COALESCE(paper_width_mm, 80) as paper_width_mm,
                        COALESCE(chars_per_line, 42) as chars_per_line
                    FROM kitchen_stationprinter
                    WHERE station_code = %s AND is_active = true
                    ORDER BY priority ASC
                    LIMIT 1
                """
                cursor.execute(query, (station_code,))

            result = cursor.fetchone()
            cursor.close()

            if not result:
                self.logger.warning(f"No printer found for station {station_code} (brand_id={brand_id})")
                return None
            
            # Get all values from database - no hardcoding!
            printer_name = result[0] or ''
            printer_ip = result[1]
            printer_port = result[2] if result[2] else 9100  # Only port has fallback
            printer_brand = result[5]  # From database
            printer_type = result[6]   # From database: 'network' or 'win32'
            timeout_seconds = result[7]  # From database
            paper_width_mm = result[8]  # From database: 58 or 80
            chars_per_line = result[9]  # From database: 32 or 42

            printer_config = {
                'name': printer_name,
                'type': printer_type,
                'host': printer_ip,
                'ip': printer_ip,
                'port': printer_port,
                'brand': printer_brand,
                'timeout': timeout_seconds,
                'paper_width_mm': paper_width_mm,
                'chars_per_line': chars_per_line,
            }

            self.logger.debug(f"Printer config for {station_code}: {printer_brand} @ {printer_ip}:{printer_port} (type: {printer_type}, {paper_width_mm}mm/{chars_per_line}cpl)")
            return printer_config
        
        except Exception as e:
            self.logger.error(f"Failed to get printer config: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None

    def fetch_checker_template(self, brand_id=None):
        """Fetch checker template from database.

        Priority: brand-specific > company-wide (brand_id IS NULL).
        Returns dict with template fields or None if not found.
        """
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT
                    header_line_1, header_line_2,
                    show_bill_number, show_table_number, show_date_time,
                    show_station_label, show_item_notes, show_item_qty,
                    show_checkbox,
                    footer_line_1, footer_line_2,
                    auto_cut, feed_lines, paper_width
                FROM kitchen_checkertemplate
                WHERE is_active = true
                  AND (brand_id = %s OR brand_id IS NULL)
                ORDER BY CASE WHEN brand_id = %s THEN 1 ELSE 2 END
                LIMIT 1
            """
            cursor.execute(query, (brand_id, brand_id))
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None

            return {
                'header_line_1': row[0] or '',
                'header_line_2': row[1] or '',
                'show_bill_number': row[2],
                'show_table_number': row[3],
                'show_date_time': row[4],
                'show_station_label': row[5],
                'show_item_notes': row[6],
                'show_item_qty': row[7],
                'show_checkbox': row[8],
                'footer_line_1': row[9] or '',
                'footer_line_2': row[10] or '',
                'auto_cut': row[11],
                'feed_lines': row[12],
                'paper_width': row[13],
            }

        except Exception as e:
            self.logger.error(f"Failed to fetch checker template: {e}")
            return None

    def fetch_kitchen_template(self, brand_id=None):
        """Fetch kitchen ticket template from database.

        Priority: brand-specific > company-wide (brand_id IS NULL).
        Returns dict with template fields or None if not found.
        """
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT
                    header_line_1, header_line_2,
                    show_bill_number, show_table_number, show_customer_name,
                    show_station_name, show_date_time, show_item_qty, show_item_notes,
                    footer_line_1, footer_line_2,
                    auto_cut, feed_lines
                FROM kitchen_kitchentickettemplate
                WHERE is_active = true
                  AND (brand_id = %s OR brand_id IS NULL)
                ORDER BY CASE WHEN brand_id = %s THEN 1 ELSE 2 END
                LIMIT 1
            """
            cursor.execute(query, (brand_id, brand_id))
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None

            return {
                'header_line_1': row[0] or '',
                'header_line_2': row[1] or '',
                'show_bill_number': row[2],
                'show_table_number': row[3],
                'show_customer_name': row[4],
                'show_station_name': row[5],
                'show_date_time': row[6],
                'show_item_qty': row[7],
                'show_item_notes': row[8],
                'footer_line_1': row[9] or '',
                'footer_line_2': row[10] or '',
                'auto_cut': row[11],
                'feed_lines': row[12],
            }

        except Exception as e:
            self.logger.error(f"Failed to fetch kitchen template: {e}")
            return None

    def get_active_printers(self, station_codes, brand_ids=None):
        """Fetch active printers for station codes"""
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT id, station_code, printer_name, printer_ip, printer_port
                FROM kitchen_stationprinter
                WHERE station_code = ANY(%s) AND is_active = true
            """
            params = [station_codes]
            if brand_ids:
                query += " AND brand_id = ANY(%s)"
                params.append(brand_ids)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            return [
                {
                    'id': r[0],
                    'station_code': r[1],
                    'printer_name': r[2] or '',
                    'printer_ip': r[3],
                    'printer_port': r[4] or 9100
                }
                for r in rows
            ]
        except Exception as e:
            self.logger.error(f"Failed to fetch active printers: {e}")
            return []

    def insert_printer_health(self, printer_id, is_online, response_time_ms=None, error_message=''):
        """Insert printer health check record"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO kitchen_printerhealthcheck
                (printer_id, checked_at, is_online, response_time_ms, paper_status, error_code, error_message, temperature_ok, cutter_ok)
                VALUES (%s, NOW(), %s, %s, 'unknown', '', %s, NULL, NULL)
                """,
                (printer_id, is_online, response_time_ms, error_message)
            )
            cursor.close()
        except Exception as e:
            self.logger.error(f"Failed to insert printer health: {e}")
    
    def fetch_pending_tickets(self, station_codes, max_tickets=10, brand_ids=None):
        """Fetch pending kitchen tickets for stations
        
        Real DB structure:
        - kitchen_kitchenticket: id, printer_target (station code), status, printer_ip, bill_id
        - pos_bill: bill_number, table_id, etc
        - pos_billitem: items dengan product info
        """
        try:
            cursor = self.conn.cursor()
            
            query = """
                SELECT
                    kt.id,
                    kt.printer_target,
                    kt.status,
                    kt.printer_ip,
                    kt.print_attempts,
                    kt.created_at,
                    kt.printed_at,
                    b.id as bill_id,
                    b.bill_number,
                    COALESCE(t.number, 'N/A') as table_number,
                    b.customer_name,
                    kt.brand_id
                FROM kitchen_kitchenticket kt
                JOIN pos_bill b ON kt.bill_id = b.id
                LEFT JOIN tables_table t ON b.table_id = t.id
                WHERE kt.printer_target = ANY(%s)
                  AND kt.status IN ('pending', 'new', 'failed')
                  AND kt.print_attempts < kt.max_retries
            """

            params = [station_codes]
            if brand_ids:
                query += " AND kt.brand_id = ANY(%s)"
                params.append(brand_ids)

            query += " ORDER BY kt.created_at ASC LIMIT %s"
            params.append(max_tickets)
            cursor.execute(query, tuple(params))
            tickets = cursor.fetchall()
            
            result = []
            for ticket in tickets:
                ticket_dict = {
                    'id': ticket[0],
                    'printer_target': ticket[1],  # This is the station code
                    'status': ticket[2],
                    'printer_ip': ticket[3],
                    'print_attempts': ticket[4],
                    'created_at': ticket[5].strftime('%Y-%m-%d %H:%M:%S') if ticket[5] else '',
                    'printed_at': ticket[6],
                    'bill_id': ticket[7],
                    'bill_number': ticket[8],
                    'table_number': ticket[9],
                    'customer_name': ticket[10] or '',
                    'brand_id': ticket[11],  # Brand ID for multi-brand printer routing
                    'items': []
                }
                
                # Fetch bill items - ONLY items in this specific ticket
                items_query = """
                    SELECT
                        bi.id,
                        kti.quantity,
                        p.name as product_name,
                        bi.notes,
                        COALESCE(bi.printer_target, '') as station
                    FROM kitchen_kitchenticketitem kti
                    JOIN pos_billitem bi ON kti.bill_item_id = bi.id
                    JOIN core_product p ON bi.product_id = p.id
                    WHERE kti.kitchen_ticket_id = %s
                    ORDER BY bi.id
                """

                cursor.execute(items_query, (ticket[0],))
                items = cursor.fetchall()

                for item in items:
                    ticket_dict['items'].append({
                        'id': item[0],
                        'quantity': item[1],
                        'product_name': item[2],
                        'notes': item[3] or '',
                        'station': item[4] or '',
                    })
                
                result.append(ticket_dict)
            
            cursor.close()
            return result
        
        except Exception as e:
            self.logger.error(f"Failed to fetch tickets: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
    
    def mark_ticket_printing(self, ticket_id):
        """Mark ticket as printing and increment attempt counter"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE kitchen_kitchenticket SET status = 'printing', print_attempts = print_attempts + 1 WHERE id = %s",
                (ticket_id,)
            )
            cursor.close()
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark printing: {e}")
            return False
    
    def mark_ticket_printed(self, ticket_id, printer_ip=None):
        """Mark ticket as printed"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE kitchen_kitchenticket 
                SET status = 'printed', 
                    printed_at = NOW() 
                WHERE id = %s
                """,
                (ticket_id,)
            )
            cursor.close()
            self.log_ticket_action(ticket_id, 'printed', 'SUCCESS', 'Ticket printed successfully', printer_ip=printer_ip)
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark printed: {e}")
            return False
    
    def mark_ticket_failed(self, ticket_id, error_message, printer_ip=None):
        """Mark ticket as failed"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE kitchen_kitchenticket SET status = 'failed' WHERE id = %s",
                (ticket_id,)
            )
            cursor.close()
            self.log_ticket_action(ticket_id, 'failed', 'ERROR', error_message, printer_ip=printer_ip)
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark failed: {e}")
            return False
    
    def log_ticket_action(self, ticket_id, new_status, action, message, old_status='', printer_ip=None, duration_ms=None):
        """Log ticket action to database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO kitchen_kitchenticketlog 
                (ticket_id, timestamp, old_status, new_status, action, actor, printer_ip, error_code, error_message, duration_ms, metadata)
                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (ticket_id, old_status, new_status, action, 'kitchen_agent', printer_ip, '', message, duration_ms, '{}')
            )
            cursor.close()
        except Exception as e:
            self.logger.error(f"Failed to log action: {e}")
    
    def update_agent_heartbeat(self, agent_name, station_ids, stats):
        """Update agent heartbeat in database (optional table)"""
        try:
            # This will fail gracefully if table doesn't exist
            cursor = self.conn.cursor()
            
            # Try to update or insert agent status
            # Note: This requires kitchen_agentstatus table to exist
            cursor.execute("""
                INSERT INTO kitchen_agentstatus 
                (agent_name, station_ids, last_heartbeat, uptime_seconds, tickets_processed, status)
                VALUES (%s, %s, NOW(), %s, %s, 'running')
                ON CONFLICT (agent_name) 
                DO UPDATE SET 
                    station_ids = EXCLUDED.station_ids,
                    last_heartbeat = NOW(),
                    uptime_seconds = EXCLUDED.uptime_seconds,
                    tickets_processed = EXCLUDED.tickets_processed,
                    status = 'running'
            """, (agent_name, json.dumps(station_ids), stats['uptime'], stats['tickets_processed']))
            
            cursor.close()
        except Exception as e:
            # Silently fail if table doesn't exist yet
            pass
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")


# ============================================================================
# HEALTH SERVER (HTTP)
# ============================================================================

class HealthRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Kitchen Agent health server.

    Endpoints:
      GET /health             -> Agent status, uptime, version
      GET /api/printers/status -> Cached printer health (from last TCP check)
    """

    def do_GET(self):
        if self.path == '/health':
            self._handle_health()
        elif self.path == '/api/printers/status':
            self._handle_printers_status()
        else:
            self._send_json(404, {'error': 'Not found'})

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _handle_health(self):
        agent = self.server.agent
        uptime = int(time.time() - agent.start_time)
        response = {
            'status': 'ok',
            'agent_name': agent.agent_name,
            'version': agent.config.get('agent', 'version', default='1.0.0'),
            'uptime_seconds': uptime,
            'tickets_processed': agent.tickets_processed,
            'station_codes': agent.station_codes,
            'poll_interval': agent.poll_interval,
            'timestamp': datetime.now().isoformat()
        }
        self._send_json(200, response)

    def _handle_printers_status(self):
        agent = self.server.agent
        printers_list = list(agent.printer_health_cache.values())

        online_count = sum(1 for p in printers_list if p.get('is_online'))
        offline_count = sum(1 for p in printers_list if not p.get('is_online'))

        if not printers_list:
            overall = 'unknown'
        elif offline_count > 0:
            overall = 'offline' if online_count == 0 else 'degraded'
        else:
            overall = 'online'

        response = {
            'overall': overall,
            'counts': {
                'total': len(printers_list),
                'online': online_count,
                'offline': offline_count,
            },
            'printers': printers_list,
            'last_check': agent.last_health_check_iso,
            'timestamp': datetime.now().isoformat()
        }
        self._send_json(200, response)

    def _send_json(self, status_code, data):
        response_bytes = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(response_bytes)

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, format, *args):
        """Suppress default stderr logging to avoid polluting agent log"""
        pass


# ============================================================================
# KITCHEN AGENT
# ============================================================================

class KitchenAgent:
    """Main kitchen printer agent"""
    
    def __init__(self, config_file='kitchen_agent_config.json'):
        # Setup logging
        self.setup_logging()
        
        # Load config
        self.logger.info("Loading configuration...")
        self.config = Config(config_file)
        
        # Initialize components
        self.logger.info("Initializing components...")
        self.db = DatabaseManager(self.config)
        self.printer = PrinterInterface(self.config)
        
        # Agent settings
        self.agent_name = self.config.get('agent', 'name', default='Kitchen-Agent-1')
        # Station codes not IDs (e.g., ['kitchen', 'bar', 'dessert'])
        self.station_codes = self.config.get('agent', 'station_codes', default=['kitchen'])
        self.brand_ids = self.config.get('agent', 'brand_ids', default=[])
        self.poll_interval = self.config.get('polling', 'interval_seconds', default=2)
        self.max_tickets = self.config.get('polling', 'max_tickets_per_poll', default=10)
        self.heartbeat_interval = self.config.get('agent', 'heartbeat_interval', default=30)
        self.health_check_interval = self.config.get('health_check', 'interval_seconds', default=60)
        self.health_check_timeout = self.config.get('health_check', 'timeout_seconds', default=5)
        
        # Health server config
        self.health_server_host = self.config.get('health_server', 'host', default='0.0.0.0')
        self.health_server_port = self.config.get('health_server', 'port', default=5001)
        self.health_server_enabled = self.config.get('health_server', 'enabled', default=True)
        self.health_server = None

        # Printer health cache (populated by check_printers_health, read by health server)
        self.printer_health_cache = {}
        self.last_health_check_iso = None

        # Statistics
        self.start_time = time.time()
        self.tickets_processed = 0
        self.last_heartbeat = 0
        self.last_health_check = 0

        self.running = False
        self.logger.info("Kitchen Agent initialized")
    
    def setup_logging(self):
        """Setup logging configuration"""
        # Get script directory for log file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(script_dir, 'kitchen_agent.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('KitchenAgent')
        self.logger.info(f"Logging to: {log_file}")
    
    def start_health_server(self):
        """Start HTTP health server on a daemon thread"""
        if not self.health_server_enabled:
            self.logger.info("Health server disabled in config")
            return

        try:
            server = HTTPServer(
                (self.health_server_host, self.health_server_port),
                HealthRequestHandler
            )
            server.agent = self  # Pass reference so handler can access agent state

            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            self.health_server = server
            self.logger.info(
                f"Health server started on {self.health_server_host}:{self.health_server_port}"
            )
        except OSError as e:
            self.logger.error(f"Failed to start health server: {e}")
            self.logger.error("Port may already be in use. Continuing without health server.")
            self.health_server = None

    def start(self):
        """Start the agent"""
        try:
            print("[DEBUG] Entering start() method")
            self.logger.info("=" * 60)
            print("[DEBUG] After first logger call")
            self.logger.info("KITCHEN PRINTER AGENT STARTED")
            self.logger.info("=" * 60)
            self.logger.info(f"Agent Name: {self.agent_name}")
            self.logger.info(f"Station Codes: {self.station_codes}")
            self.logger.info(f"Brand IDs: {self.brand_ids if self.brand_ids else 'ALL'}")
            self.logger.info(f"Poll Interval: {self.poll_interval}s")
            self.logger.info(f"Heartbeat Interval: {self.heartbeat_interval}s")
            self.logger.info(f"Health Check Interval: {self.health_check_interval}s")
            self.logger.info("=" * 60)
            
            # Start HTTP health server (non-blocking daemon thread)
            self.start_health_server()

            print("[DEBUG] Logger setup complete, entering loop")
            self.running = True
            
            while self.running:
                print("[DEBUG] Loop iteration")
                try:
                    self.process_tickets()
                except Exception as e:
                    self.logger.error(f"Error in process_tickets: {e}")
                    print(f"[DEBUG] Error in loop: {e}")
                
                try:
                    self.send_heartbeat()
                except Exception as e:
                    self.logger.error(f"Error in send_heartbeat: {e}")
                
                try:
                    self.check_printers_health()
                except Exception as e:
                    self.logger.error(f"Error in check_printers_health: {e}")
                
                time.sleep(self.poll_interval)
        
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested (Ctrl+C)")
        
        except Exception as e:
            print(f"[DEBUG] Exception caught: {e}")
            self.logger.error(f"Unexpected error in start(): {e}")
            import traceback
            traceback.print_exc()
            self.logger.error(traceback.format_exc())
            raise
        
        finally:
            print("[DEBUG] In finally block")
            self.stop()
    
    def process_tickets(self):
        """Process pending tickets for all stations"""
        try:
            # Fetch tickets for all monitored stations
            self.logger.info(f"Checking for tickets - Stations: {self.station_codes}")
            tickets = self.db.fetch_pending_tickets(self.station_codes, self.max_tickets, self.brand_ids)
            
            self.logger.info(f"Fetched {len(tickets)} ticket(s)")
            
            if tickets:
                self.logger.info(f"Found {len(tickets)} pending ticket(s)")
                
                for ticket in tickets:
                    self.process_single_ticket(ticket)
            else:
                self.logger.debug("No pending tickets found")
        
        except Exception as e:
            self.logger.error(f"Error processing tickets: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def process_single_ticket(self, ticket):
        """Process a single ticket"""
        ticket_id = ticket['id']
        bill_number = ticket['bill_number']
        printer_target = ticket['printer_target']
        brand_id = ticket.get('brand_id')

        self.logger.info(f"Processing bill #{bill_number} (ID: {ticket_id}, Target: {printer_target}, Brand: {brand_id})")

        try:
            # Get printer config from database using printer_target + brand_id
            # brand_id ensures correct routing in multi-brand food courts
            printer_config = self.db.get_printer_for_station(printer_target, brand_id=brand_id)

            if not printer_config:
                error_msg = f"No printer configured for station {printer_target} (brand_id={brand_id})"
                self.logger.error(error_msg)
                self.db.mark_ticket_failed(ticket_id, error_msg)
                return
            
            printer_ip = printer_config['ip']
            
            # Mark as printing
            if not self.db.mark_ticket_printing(ticket_id):
                self.logger.error(f"Failed to mark ticket {ticket_id} as printing")
                return
            
            # Print ticket with dynamic config (pass db for checker template lookup)
            success = self.printer.print_ticket(ticket, printer_config, db=self.db)
            
            if success:
                # Mark as printed
                self.db.mark_ticket_printed(ticket_id, printer_ip=printer_ip)
                self.tickets_processed += 1
                self.logger.info(f"✓ Bill #{bill_number} printed successfully")
            else:
                # Mark as failed
                self.db.mark_ticket_failed(ticket_id, "Print failed", printer_ip=printer_ip)
                self.logger.error(f"✗ Bill #{bill_number} print failed")
        
        except Exception as e:
            self.logger.error(f"Error processing ticket {ticket_id}: {e}")
            self.db.mark_ticket_failed(ticket_id, str(e))
    
    def send_heartbeat(self):
        """Send heartbeat to database"""
        current_time = time.time()
        
        # Only send heartbeat at specified interval
        if current_time - self.last_heartbeat < self.heartbeat_interval:
            return
        
        try:
            uptime = int(current_time - self.start_time)
            stats = {
                'uptime': uptime,
                'tickets_processed': self.tickets_processed
            }
            
            self.db.update_agent_heartbeat(self.agent_name, self.station_codes, stats)
            self.last_heartbeat = current_time
            
            # Log heartbeat every 5 minutes
            if uptime % 300 == 0:
                self.logger.info(f"Heartbeat: {self.agent_name} | Uptime: {uptime}s | Processed: {self.tickets_processed}")
        
        except Exception as e:
            # Don't fail agent if heartbeat fails
            pass

    def check_printers_health(self):
        """Check printer connectivity and store health checks"""
        current_time = time.time()
        if current_time - self.last_health_check < self.health_check_interval:
            return

        try:
            printers = self.db.get_active_printers(self.station_codes, self.brand_ids)
            if not printers:
                self.last_health_check = current_time
                return

            for printer in printers:
                start_time = time.time()
                is_online = False
                response_time_ms = None
                error_message = ''

                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(self.health_check_timeout)
                    result = sock.connect_ex((str(printer['printer_ip']), int(printer['printer_port'])))
                    sock.close()

                    response_time_ms = int((time.time() - start_time) * 1000)
                    if result == 0:
                        is_online = True
                    else:
                        error_message = f'Connection failed with code {result}'
                except Exception as e:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    error_message = str(e)

                self.db.insert_printer_health(
                    printer_id=printer['id'],
                    is_online=is_online,
                    response_time_ms=response_time_ms,
                    error_message=error_message
                )

                # Cache result for health server HTTP endpoint
                self.printer_health_cache[printer['id']] = {
                    'id': printer['id'],
                    'station_code': printer['station_code'],
                    'printer_name': printer.get('printer_name', ''),
                    'printer_ip': printer['printer_ip'],
                    'printer_port': printer['printer_port'],
                    'is_online': is_online,
                    'response_time_ms': response_time_ms,
                    'error_message': error_message,
                    'checked_at': datetime.now().isoformat()
                }

            self.last_health_check = current_time
            self.last_health_check_iso = datetime.now().isoformat()

        except Exception:
            # Don't fail agent if health check fails
            self.last_health_check = current_time
    
    def stop(self):
        """Stop the agent"""
        self.logger.info("Stopping Kitchen Agent...")
        self.running = False

        # Shutdown health server
        if self.health_server:
            try:
                self.health_server.shutdown()
                self.logger.info("Health server stopped")
            except Exception:
                pass

        if self.db:
            self.db.close()

        self.logger.info("Kitchen Agent stopped")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("KITCHEN PRINTER AGENT")
    print("Version 1.0.0")
    print("=" * 60 + "\n")
    
    # Check dependencies
    if not HAS_PSYCOPG2:
        print("[ERROR] psycopg2 is required!")
        print("Install: pip install psycopg2-binary")
        sys.exit(1)
    
    # Create and start agent
    try:
        print("[INFO] Initializing agent...")
        agent = KitchenAgent()
        print("[INFO] Starting agent...")
        agent.start()
    
    except Exception as e:
        print(f"\n[ERROR] Failed to start agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
