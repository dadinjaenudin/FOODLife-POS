"""
ESC/POS Printer module
Handles formatting and printing to thermal printers
Supports HRPT and other thermal printers
"""
import socket
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ESC/POS Commands (HRPT-compatible)
ESC = b'\x1b'
GS = b'\x1d'
INIT = ESC + b'@'  # CRITICAL for HRPT - clears all formatting
CUT_PAPER = ESC + b'd\x03' + ESC + b'm'
ALIGN_CENTER = ESC + b'a\x01'
ALIGN_LEFT = ESC + b'a\x00'
BOLD_ON = ESC + b'E\x01'
BOLD_OFF = ESC + b'E\x00'

# Font sizing using GS ! (works on HRPT)
NORMAL_SIZE = GS + b'!\x00'  # 1x width, 1x height
DOUBLE_SIZE = GS + b'!\x11'  # 2x width, 2x height
DOUBLE_WIDTH = GS + b'!\x10'  # 2x width, 1x height
DOUBLE_HEIGHT = GS + b'!\x01'  # 1x width, 2x height

LINE_FEED = b'\n'


def test_printer_connection(ip: str, port: int, timeout: int = 3) -> bool:
    """
    Test if printer is reachable
    Returns True if connection successful
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result == 0:
            logger.info(f"✓ Printer {ip}:{port} is reachable")
            return True
        else:
            logger.warning(f"✗ Printer {ip}:{port} is NOT reachable")
            return False
            
    except Exception as e:
        logger.error(f"Error testing printer connection: {e}")
        return False


def format_kitchen_ticket(ticket: Dict, items: List[Dict], chars_per_line: int = 32) -> bytes:
    """
    Format ticket data into ESC/POS commands
    
    Args:
        ticket: Ticket data from database
        items: List of items from database
        chars_per_line: Printer character width (32 for 80mm, 24 for 58mm)
    
    Returns:
        bytes: ESC/POS command sequence
    """
    output = bytearray()
    
    # Initialize printer
    output.extend(INIT)
    
    # Header - Center aligned
    output.extend(ALIGN_CENTER)
    output.extend(DOUBLE_SIZE)
    output.extend(b'================================')
    output.extend(LINE_FEED)
    output.extend(b'   KITCHEN ORDER')
    output.extend(LINE_FEED)
    output.extend(b'================================')
    output.extend(LINE_FEED)
    output.extend(NORMAL_SIZE)
    output.extend(LINE_FEED)
    
    # Order info - Left aligned
    output.extend(ALIGN_LEFT)
    output.extend(BOLD_ON)
    
    # Table and time info
    table_info = f"Table: {ticket.get('table_id', 'N/A')}".ljust(16)
    time_info = datetime.now().strftime("%H:%M")
    output.extend(f"{table_info}Time: {time_info}".encode('utf-8'))
    output.extend(LINE_FEED)
    
    # Bill number
    output.extend(f"Order: #{ticket.get('bill_number', 'N/A')}".encode('utf-8'))
    output.extend(LINE_FEED)
    output.extend(BOLD_OFF)
    output.extend(LINE_FEED)
    
    # Separator
    output.extend(b'--------------------------------')
    output.extend(LINE_FEED)
    output.extend(BOLD_ON)
    output.extend(b'ITEMS:')
    output.extend(LINE_FEED)
    output.extend(BOLD_OFF)
    output.extend(b'--------------------------------')
    output.extend(LINE_FEED)
    
    # Items list
    for item in items:
        qty = item.get('quantity', 1)
        menu_name = item.get('menu_name', 'Unknown Item')
        notes = item.get('notes', '')
        
        # Item line with quantity
        output.extend(BOLD_ON)
        item_line = f"{qty}x {menu_name}"
        output.extend(item_line.encode('utf-8'))
        output.extend(LINE_FEED)
        output.extend(BOLD_OFF)
        
        # Notes if any
        if notes:
            # Split notes by newline and indent
            for note_line in notes.split('\n'):
                if note_line.strip():
                    output.extend(f"   {note_line.strip()}".encode('utf-8'))
                    output.extend(LINE_FEED)
        
        output.extend(LINE_FEED)
    
    # Footer separator
    output.extend(b'================================')
    output.extend(LINE_FEED)
    
    # Station info
    station = ticket.get('printer_target', 'KITCHEN').upper()
    output.extend(f"Station: {station}".encode('utf-8'))
    output.extend(LINE_FEED)
    
    # Brand name
    brand = ticket.get('brand_name', '')
    if brand:
        output.extend(f"Brand: {brand}".encode('utf-8'))
        output.extend(LINE_FEED)
    
    # Ticket ID for reference
    output.extend(f"Ticket ID: #{ticket.get('id')}".encode('utf-8'))
    output.extend(LINE_FEED)
    
    output.extend(b'================================')
    output.extend(LINE_FEED)
    output.extend(LINE_FEED)
    output.extend(LINE_FEED)
    
    # Cut paper
    output.extend(CUT_PAPER)
    
    return bytes(output)


def print_to_network_printer(ip: str, port: int, data: bytes, timeout: int = 10) -> bool:
    """
    Send data to network printer via raw socket
    
    Args:
        ip: Printer IP address
        port: Printer port (usually 9100)
        data: ESC/POS command bytes
        timeout: Socket timeout in seconds
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # Connect to printer
        logger.info(f"Connecting to printer {ip}:{port}...")
        sock.connect((ip, port))
        
        # Send data
        logger.info(f"Sending {len(data)} bytes to printer...")
        sock.sendall(data)
        
        # Close connection
        sock.close()
        
        logger.info(f"✓ Print job sent successfully to {ip}:{port}")
        return True
        
    except socket.timeout:
        logger.error(f"✗ Timeout connecting to printer {ip}:{port}")
        return False
    except ConnectionRefusedError:
        logger.error(f"✗ Connection refused by printer {ip}:{port}")
        return False
    except Exception as e:
        logger.error(f"✗ Error printing to {ip}:{port}: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass


def print_ticket(printer_config: Dict, ticket: Dict) -> bool:
    """
    Main function to print kitchen ticket
    
    Args:
        printer_config: Printer configuration from database
        ticket: Ticket data with items
    
    Returns:
        bool: True if print successful
    """
    try:
        # Extract printer info
        ip = printer_config['printer_ip']
        port = printer_config['printer_port']
        chars_per_line = printer_config.get('chars_per_line', 32)
        
        # Test connection first
        if not test_printer_connection(ip, port, timeout=3):
            raise Exception(f"Printer {ip}:{port} is not reachable")
        
        # Format ticket
        logger.info(f"Formatting ticket #{ticket['id']} for {printer_config['printer_name']}")
        escpos_data = format_kitchen_ticket(ticket, ticket.get('items', []), chars_per_line)
        
        # Print
        success = print_to_network_printer(ip, port, escpos_data, timeout=10)
        
        if success:
            logger.info(f"✓ Ticket #{ticket['id']} printed successfully on {printer_config['printer_name']}")
        else:
            logger.error(f"✗ Failed to print ticket #{ticket['id']} on {printer_config['printer_name']}")
        
        return success
        
    except Exception as e:
        logger.error(f"✗ Error printing ticket #{ticket.get('id')}: {e}")
        return False
