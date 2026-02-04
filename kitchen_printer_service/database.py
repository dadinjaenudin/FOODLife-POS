"""
Database module for Kitchen Printer Service
Handles all PostgreSQL interactions
"""
import psycopg2
import psycopg2.extras
from datetime import datetime
import logging
from typing import List, Dict, Optional
import json

from config import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
)

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """PostgreSQL database connection manager"""
    
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            # Use autocommit for this service - we manage transactions explicitly
            self.conn.autocommit = True
            logger.info(f"✓ Connected to database: {DB_NAME}@{DB_HOST}:{DB_PORT}")
        except Exception as e:
            logger.error(f"✗ Database connection failed: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def test_connection(self):
        """Test database connection"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


def fetch_pending_tickets(conn, limit: int = 10) -> List[Dict]:
    """
    Fetch tickets with status='new', ordered by created_at ASC
    
    Returns list of tickets with their items
    """
    query = """
        SELECT 
            t.id,
            t.bill_id,
            t.printer_target,
            t.status,
            t.print_attempts,
            t.max_retries,
            t.created_at,
            b.bill_number,
            b.table_id,
            br.name as brand_name
        FROM kitchen_kitchenticket t
        JOIN pos_bill b ON t.bill_id = b.id
        JOIN core_brand br ON b.brand_id = br.id
        WHERE t.status = 'new'
        ORDER BY t.created_at ASC
        LIMIT %s
        FOR UPDATE SKIP LOCKED
    """
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (limit,))
            tickets = cur.fetchall()
            
            # Fetch items for each ticket
            for ticket in tickets:
                items_query = """
                    SELECT 
                        ti.quantity,
                        p.name as menu_name,
                        bi.notes
                    FROM kitchen_kitchenticketitem ti
                    JOIN pos_billitem bi ON ti.bill_item_id = bi.id
                    JOIN core_product p ON bi.product_id = p.id
                    WHERE ti.kitchen_ticket_id = %s
                """
                cur.execute(items_query, (ticket['id'],))
                ticket['items'] = cur.fetchall()
            
            logger.info(f"Fetched {len(tickets)} pending tickets")
            return tickets
            
    except Exception as e:
        # No need for rollback with autocommit=True
        logger.error(f"Error fetching pending tickets: {e}")
        return []


def get_printer_for_station(conn, station_code: str, brand_id: str) -> Optional[Dict]:
    """
    Get active printer for station, ordered by priority ASC (1=primary, 2=backup)
    
    Returns printer config or None if no printer available
    """
    query = """
        SELECT 
            id,
            station_code,
            printer_name,
            printer_ip,
            printer_port,
            paper_width_mm,
            chars_per_line,
            priority
        FROM kitchen_stationprinter
        WHERE station_code = %s
          AND brand_id = %s
          AND is_active = true
        ORDER BY priority ASC
        LIMIT 1
    """
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (station_code, brand_id))
            printer = cur.fetchone()
            
            if printer:
                logger.info(f"Found printer: {printer['printer_name']} ({printer['printer_ip']}) for station '{station_code}'")
            else:
                logger.warning(f"No active printer found for station '{station_code}'")
            
            return printer
            
    except Exception as e:
        logger.error(f"Error fetching printer: {e}")
        return None


def mark_ticket_printing(conn, ticket_id: int, printer_ip: str):
    """Mark ticket as 'printing' and increment print_attempts"""
    query = """
        UPDATE kitchen_kitchenticket
        SET status = 'printing',
            printer_ip = %s,
            print_attempts = print_attempts + 1
        WHERE id = %s
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, (printer_ip, ticket_id))
            # No commit needed with autocommit=True
            logger.info(f"Ticket #{ticket_id} marked as PRINTING (printer: {printer_ip})")
            
            # Log action
            log_ticket_action(conn, ticket_id, 'print_start', 'printer_service', {
                'printer_ip': printer_ip
            })
            
    except Exception as e:
        logger.error(f"Error marking ticket #{ticket_id} as printing: {e}")
        raise


def mark_ticket_printed(conn, ticket_id: int):
    """Mark ticket as 'printed' with timestamp"""
    query = """
        UPDATE kitchen_kitchenticket
        SET status = 'printed',
            printed_at = NOW()
        WHERE id = %s
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, (ticket_id,))
            logger.info(f"✓ Ticket #{ticket_id} marked as PRINTED")
            
            # Log action
            log_ticket_action(conn, ticket_id, 'print_success', 'printer_service')
            
    except Exception as e:
        logger.error(f"Error marking ticket #{ticket_id} as printed: {e}")
        raise


def mark_ticket_failed(conn, ticket_id: int, error_message: str):
    """Mark ticket as 'failed' with error message"""
    query = """
        UPDATE kitchen_kitchenticket
        SET status = 'failed',
            error_message = %s,
            last_error_at = NOW()
        WHERE id = %s
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, (error_message, ticket_id))
            logger.error(f"✗ Ticket #{ticket_id} marked as FAILED: {error_message}")
            
            # Log action
            log_ticket_action(conn, ticket_id, 'print_failed', 'printer_service', {
                'error': error_message
            })
            
    except Exception as e:
        logger.error(f"Error marking ticket #{ticket_id} as failed: {e}")
        raise


def mark_ticket_new_for_retry(conn, ticket_id: int):
    """Reset ticket to 'new' status for retry"""
    query = """
        UPDATE kitchen_kitchenticket
        SET status = 'new'
        WHERE id = %s
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, (ticket_id,))
            logger.info(f"Ticket #{ticket_id} reset to NEW for retry")
            
            # Log action
            log_ticket_action(conn, ticket_id, 'retry', 'printer_service')
            
    except Exception as e:
        logger.error(f"Error resetting ticket #{ticket_id}: {e}")
        raise


def log_ticket_action(conn, ticket_id: int, action: str, actor: str, metadata: Dict = None):
    """Log ticket action to kitchen_kitchenticketlog"""
    
    # Get old status from ticket
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT status FROM kitchen_kitchenticket WHERE id = %s", (ticket_id,))
            result = cur.fetchone()
            old_status = result['status'] if result else ''
    except:
        old_status = ''
    
    # Determine new status based on action
    new_status = old_status  # default to same
    if action == 'print_start':
        new_status = 'printing'
    elif action == 'print_success':
        new_status = 'printed'
    elif action == 'print_failed':
        new_status = 'failed'
    elif action == 'retry':
        new_status = 'new'
    elif action == 'created':
        new_status = 'new'
        old_status = ''  # no previous status
    
    query = """
        INSERT INTO kitchen_kitchenticketlog (
            ticket_id,
            timestamp,
            old_status,
            new_status,
            action,
            actor,
            printer_ip,
            error_code,
            error_message,
            duration_ms,
            metadata
        ) VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, (
                ticket_id,
                old_status,
                new_status,
                action,
                actor,
                None,          # printer_ip
                '',            # error_code - default empty
                '',            # error_message - default empty
                None,          # duration_ms
                json.dumps({}) # metadata - default empty dict
            ))
            
    except Exception as e:
        logger.error(f"Error logging action for ticket #{ticket_id}: {e}")


def update_printer_stats(conn, printer_id: int, success: bool = True):
    """Update printer statistics"""
    if success:
        query = """
            UPDATE kitchen_stationprinter
            SET total_prints = total_prints + 1,
                last_print_at = NOW()
            WHERE id = %s
        """
    else:
        query = """
            UPDATE kitchen_stationprinter
            SET failed_prints = failed_prints + 1,
                last_error_at = NOW()
            WHERE id = %s
        """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, (printer_id,))
            
    except Exception as e:
        logger.error(f"Error updating printer stats: {e}")


def get_service_stats(conn) -> Dict:
    """Get service statistics for health check"""
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Pending tickets
            cur.execute("SELECT COUNT(*) as count FROM kitchen_kitchenticket WHERE status = 'new'")
            pending = cur.fetchone()['count']
            
            # Total printed today
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM kitchen_kitchenticket 
                WHERE status = 'printed' 
                AND DATE(printed_at) = CURRENT_DATE
            """)
            printed_today = cur.fetchone()['count']
            
            # Failed tickets
            cur.execute("SELECT COUNT(*) as count FROM kitchen_kitchenticket WHERE status = 'failed'")
            failed = cur.fetchone()['count']
            
            return {
                'pending_tickets': pending,
                'printed_today': printed_today,
                'failed_tickets': failed
            }
            
    except Exception as e:
        logger.error(f"Error getting service stats: {e}")
        return {}
