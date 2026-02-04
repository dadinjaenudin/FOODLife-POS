"""
Main service loop for Kitchen Printer Service
Polls database for pending tickets and prints them
"""
import sys
import time
import signal
import logging
from datetime import datetime

from config import (
    POLL_INTERVAL,
    MAX_TICKETS_PER_POLL,
    HEALTH_CHECK_PORT,
    log_config
)
from database import (
    DatabaseConnection,
    fetch_pending_tickets,
    get_printer_for_station,
    mark_ticket_printing,
    mark_ticket_printed,
    mark_ticket_failed,
    mark_ticket_new_for_retry,
    update_printer_stats
)
from printer import print_ticket
from health import (
    start_health_server,
    set_db_connection,
    increment_processed,
    increment_failed,
    update_last_poll
)

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    running = False


def process_ticket(conn, ticket):
    """
    Process a single ticket: fetch printer, print, update status
    
    Args:
        conn: Database connection
        ticket: Ticket data dict
    
    Returns:
        bool: True if processed successfully
    """
    ticket_id = ticket['id']
    printer_target = ticket['printer_target']
    bill_number = ticket['bill_number']
    brand_id = ticket.get('brand_id')  # Assuming brand_id is in the ticket query
    
    logger.info(f"Processing ticket #{ticket_id} - {bill_number} [{printer_target.upper()}]")
    
    try:
        # Get printer for this station
        # Note: We need to get brand_id from the bill, let's fetch it
        query = """
            SELECT brand_id 
            FROM pos_bill 
            WHERE id = %s
        """
        with conn.cursor() as cur:
            cur.execute(query, (ticket['bill_id'],))
            result = cur.fetchone()
            if result:
                brand_id = result[0]
        
        printer = get_printer_for_station(conn, printer_target, brand_id)
        
        if not printer:
            error_msg = f"No active printer found for station '{printer_target}'"
            logger.error(f"✗ Ticket #{ticket_id}: {error_msg}")
            mark_ticket_failed(conn, ticket_id, error_msg)
            increment_failed()
            return False
        
        # Mark as printing
        mark_ticket_printing(conn, ticket_id, printer['printer_ip'])
        
        # Print ticket
        logger.info(f"Printing ticket #{ticket_id} to {printer['printer_name']} ({printer['printer_ip']}:{printer['printer_port']})")
        
        success = print_ticket(printer, ticket)
        
        if success:
            # Mark as printed
            mark_ticket_printed(conn, ticket_id)
            update_printer_stats(conn, printer['id'], success=True)
            increment_processed()
            logger.info(f"✓ Ticket #{ticket_id} completed successfully")
            return True
        else:
            # Print failed
            error_msg = f"Failed to print to {printer['printer_ip']}:{printer['printer_port']}"
            
            # Check if can retry
            if ticket['print_attempts'] < ticket['max_retries']:
                logger.warning(f"⟳ Ticket #{ticket_id} will be retried (attempt {ticket['print_attempts'] + 1}/{ticket['max_retries']})")
                mark_ticket_new_for_retry(conn, ticket_id)
            else:
                logger.error(f"✗ Ticket #{ticket_id} max retries exceeded")
                mark_ticket_failed(conn, ticket_id, error_msg)
                increment_failed()
            
            update_printer_stats(conn, printer['id'], success=False)
            return False
            
    except Exception as e:
        error_msg = f"Exception processing ticket: {str(e)}"
        logger.exception(f"✗ Ticket #{ticket_id}: {error_msg}")
        
        try:
            mark_ticket_failed(conn, ticket_id, error_msg)
            increment_failed()
        except:
            logger.error(f"Failed to mark ticket #{ticket_id} as failed")
        
        return False


def main_loop():
    """Main service loop"""
    global running
    
    # Log configuration
    log_config()
    
    # Connect to database
    logger.info("Connecting to database...")
    db = DatabaseConnection()
    
    # Start health check server
    set_db_connection(db)
    start_health_server(HEALTH_CHECK_PORT)
    
    logger.info("=" * 60)
    logger.info("Kitchen Printer Service is running")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    
    # Main polling loop
    while running:
        try:
            update_last_poll()
            
            # Fetch pending tickets
            tickets = fetch_pending_tickets(db.conn, limit=MAX_TICKETS_PER_POLL)
            
            if not tickets:
                # No tickets, sleep and continue
                time.sleep(POLL_INTERVAL)
                continue
            
            logger.info(f"Found {len(tickets)} pending ticket(s), processing...")
            
            # Process each ticket
            for ticket in tickets:
                if not running:
                    break
                
                process_ticket(db.conn, ticket)
                
                # Small delay between tickets to avoid overwhelming printer
                time.sleep(0.5)
            
            # Sleep before next poll
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            running = False
            break
            
        except Exception as e:
            logger.exception(f"Error in main loop: {e}")
            # Sleep longer on error to avoid rapid error loops
            time.sleep(5)
    
    # Cleanup
    logger.info("Shutting down...")
    db.close()
    logger.info("✓ Kitchen Printer Service stopped")


if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        main_loop()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
