"""
Kitchen Network Printer Helper
Direct ESC/POS printing from Django using python-escpos
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from escpos.printer import Network
    HAS_ESCPOS = True
except ImportError:
    HAS_ESCPOS = False
    logger.warning("python-escpos not available")


class NetworkPrinterHelper:
    """
    Helper class for ESC/POS network printing
    Supports HRPT and other thermal printers
    """
    
    def __init__(self, ip: str, port: int = 9100, timeout: int = 3):
        """
        Initialize network printer connection
        
        Args:
            ip: Printer IP address or hostname
            port: Printer port (default 9100)
            timeout: Connection timeout in seconds
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.printer = None
    
    def connect(self) -> bool:
        """
        Connect to network printer
        Returns True if successful
        """
        if not HAS_ESCPOS:
            logger.error("python-escpos not installed")
            return False
        
        try:
            self.printer = Network(self.ip, port=self.port)
            logger.info(f"Connected to printer {self.ip}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.ip}:{self.port} - {e}")
            return False
    
    def print_test(self) -> bool:
        """
        Send test print to printer
        Returns True if successful
        """
        if not self.connect():
            return False
        
        try:
            # Initialize printer
            self.printer.hw('INIT')
            
            # Center align, double size
            self.printer.set(align='center', double_width=True, double_height=True)
            self.printer.text("=== TEST PRINT ===\n")
            
            # Normal text, left align
            self.printer.set(align='left', double_width=False, double_height=False)
            self.printer.text("\n")
            self.printer.text(f"Printer: {self.ip}:{self.port}\n")
            self.printer.text(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.printer.text("\n")
            self.printer.text("Test from Django\n")
            self.printer.text("YOGYA FOODLIFE POS\n")
            self.printer.text("\n")
            self.printer.text("==================\n")
            self.printer.text("\n\n\n")
            
            # Cut paper
            self.printer.cut()
            self.printer.close()
            
            logger.info(f"Test print sent to {self.ip}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Print error: {e}")
            if self.printer:
                try:
                    self.printer.close()
                except:
                    pass
            return False
    
    def print_kitchen_ticket(self, ticket_data: Dict, items: List[Dict]) -> bool:
        """
        Print kitchen order ticket
        
        Args:
            ticket_data: Ticket info (table, bill_number, etc)
            items: List of order items
        
        Returns:
            True if successful
        """
        if not self.connect():
            return False
        
        try:
            # Initialize
            self.printer.hw('INIT')
            
            # Header - Center, Bold, Double size
            self.printer.set(align='center', bold=True, double_width=True, double_height=True)
            self.printer.text("================================\n")
            self.printer.text("   KITCHEN ORDER\n")
            self.printer.text("================================\n")
            self.printer.text("\n")
            
            # Order info - Left align, normal size
            self.printer.set(align='left', bold=False, double_width=False, double_height=False)
            
            table_info = f"Table: {ticket_data.get('table_id', 'N/A')}".ljust(16)
            time_info = datetime.now().strftime("%H:%M")
            self.printer.text(f"{table_info}Time: {time_info}\n")
            self.printer.text(f"Order: #{ticket_data.get('bill_number', 'N/A')}\n")
            self.printer.text("\n")
            
            # Separator
            self.printer.text("--------------------------------\n")
            self.printer.set(bold=True)
            self.printer.text("ITEMS:\n")
            self.printer.set(bold=False)
            self.printer.text("--------------------------------\n")
            
            # Items list
            for idx, item in enumerate(items, 1):
                qty = item.get('quantity', 1)
                name = item.get('menu_name', 'Unknown')
                
                # Format: "1. 2x Nasi Goreng"
                self.printer.text(f"{idx}. {qty}x {name}\n")
                
                # Notes if any
                notes = item.get('notes', '')
                if notes:
                    self.printer.text(f"   Note: {notes}\n")
            
            # Footer
            self.printer.text("--------------------------------\n")
            self.printer.text("\n")
            
            # Station info
            station = ticket_data.get('printer_target', 'KITCHEN').upper()
            self.printer.set(align='center', bold=True)
            self.printer.text(f"[ {station} STATION ]\n")
            self.printer.text("\n\n\n\n")
            
            # Cut paper
            self.printer.cut()
            self.printer.close()
            
            logger.info(f"Kitchen ticket printed to {self.ip}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Print error: {e}")
            if self.printer:
                try:
                    self.printer.close()
                except:
                    pass
            return False


def test_network_printer(ip: str, port: int = 9100) -> tuple[bool, str]:
    """
    Test network printer connection and print
    
    Args:
        ip: Printer IP or hostname
        port: Printer port
    
    Returns:
        (success: bool, message: str)
    """
    try:
        helper = NetworkPrinterHelper(ip, port)
        success = helper.print_test()
        
        if success:
            return True, f"Test print sent successfully to {ip}:{port}"
        else:
            return False, f"Failed to print to {ip}:{port}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"
