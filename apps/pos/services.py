"""POS services for printing and other operations"""


def print_receipt(bill):
    """
    DEPRECATED: Direct print function replaced by queue-based printing
    
    All printing should now use queue_print_receipt() from print_queue.py
    This ensures consistent HRPT-compatible printing via Print Agent.
    
    Keeping function for backward compatibility but raises error.
    """
    raise DeprecationWarning(
        "Direct printing is deprecated. "
        "Use queue_print_receipt(bill, terminal_id) from apps.pos.print_queue instead."
    )
