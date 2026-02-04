"""
Configuration module for Kitchen Printer Service
Loads settings from environment variables
"""
import os
import logging

# Database Configuration
DB_HOST = os.getenv('DB_HOST', 'edge_db')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'fnb_edge_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres123')

# Service Configuration
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '2'))  # seconds
MAX_TICKETS_PER_POLL = int(os.getenv('MAX_TICKETS_PER_POLL', '10'))
HEALTH_CHECK_PORT = int(os.getenv('HEALTH_CHECK_PORT', '9100'))

# Retry Configuration
MAX_PRINT_RETRIES = int(os.getenv('MAX_PRINT_RETRIES', '3'))
RETRY_DELAY_SECONDS = int(os.getenv('RETRY_DELAY_SECONDS', '5'))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def get_db_connection_string():
    """Get PostgreSQL connection string"""
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def log_config():
    """Log current configuration (without sensitive data)"""
    logger.info("=" * 60)
    logger.info("Kitchen Printer Service Configuration")
    logger.info("=" * 60)
    logger.info(f"Database Host: {DB_HOST}:{DB_PORT}")
    logger.info(f"Database Name: {DB_NAME}")
    logger.info(f"Poll Interval: {POLL_INTERVAL}s")
    logger.info(f"Max Tickets Per Poll: {MAX_TICKETS_PER_POLL}")
    logger.info(f"Health Check Port: {HEALTH_CHECK_PORT}")
    logger.info(f"Max Print Retries: {MAX_PRINT_RETRIES}")
    logger.info(f"Log Level: {LOG_LEVEL}")
    logger.info("=" * 60)
