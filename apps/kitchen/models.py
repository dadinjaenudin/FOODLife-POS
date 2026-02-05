from django.db import models
from django.utils import timezone
from datetime import timedelta


class PrinterBrand(models.Model):
    """
    Printer brand/model reference for ESC/POS command profiles
    """
    code = models.CharField(
        max_length=20, 
        unique=True,
        help_text='Brand code: HRPT, EPSON, XPRINTER'
    )
    name = models.CharField(max_length=100, help_text='Display name')
    profile_class = models.CharField(
        max_length=50,
        help_text='Python class name: HRPTProfile, EpsonProfile'
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Printer Brand'
        verbose_name_plural = 'Printer Brands'
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class KitchenOrder(models.Model):
    """Aggregated view for KDS"""
    STATUS_CHOICES = [
        ('new', 'New'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
    ]
    
    PRIORITY_CHOICES = [
        ('normal', 'Normal'),
        ('rush', 'Rush'),
        ('urgent', 'Urgent'),
    ]
    
    bill = models.ForeignKey('pos.Bill', on_delete=models.CASCADE, related_name='kitchen_orders')
    station = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Timer tracking
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Performance targets (in minutes)
    target_prep_time = models.IntegerField(default=15, help_text="Target preparation time in minutes")
    
    # Notification flags
    notified_10min = models.BooleanField(default=False)
    notified_overdue = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-priority', 'created_at']
        # CRITICAL: Prevent duplicate orders for same bill+station
        unique_together = [['bill', 'station']]
        indexes = [
            models.Index(fields=['bill', 'station']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['priority', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.bill.bill_number} - {self.station}"
    
    def get_elapsed_time(self):
        """Get elapsed time since order created (in seconds)"""
        if self.status in ['ready', 'served'] and self.completed_at:
            return int((self.completed_at - self.created_at).total_seconds())
        return int((timezone.now() - self.created_at).total_seconds())
    
    def get_elapsed_minutes(self):
        """Get elapsed time in minutes"""
        return self.get_elapsed_time() // 60
    
    def get_prep_time(self):
        """Get actual preparation time (started to completed) in seconds"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        elif self.started_at:
            return int((timezone.now() - self.started_at).total_seconds())
        return 0
    
    def is_overdue(self):
        """Check if order exceeded target prep time"""
        if self.status in ['ready', 'served']:
            return False
        elapsed_minutes = self.get_elapsed_minutes()
        return elapsed_minutes > self.target_prep_time
    
    def get_time_status(self):
        """Get time status: on_time, warning, overdue"""
        if self.status in ['ready', 'served']:
            return 'completed'
        
        elapsed_minutes = self.get_elapsed_minutes()
        
        if elapsed_minutes > self.target_prep_time:
            return 'overdue'
        elif elapsed_minutes > (self.target_prep_time * 0.7):  # 70% threshold
            return 'warning'
        else:
            return 'on_time'
    
    def get_time_color(self):
        """Get color based on time status"""
        status = self.get_time_status()
        colors = {
            'on_time': 'green',
            'warning': 'yellow',
            'overdue': 'red',
            'completed': 'blue',
        }
        return colors.get(status, 'gray')


class KitchenStation(models.Model):
    """Kitchen station configuration"""
    brand = models.ForeignKey('core.Brand', on_delete=models.CASCADE, related_name='kitchen_stations')
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20)  # e.g., 'kitchen', 'bar', 'grill', 'dessert'
    
    # Performance settings
    target_prep_time = models.IntegerField(default=15, help_text="Default target prep time in minutes")
    warning_threshold = models.IntegerField(default=10, help_text="Warning at X minutes")
    
    # Display settings
    color = models.CharField(max_length=20, default='blue')
    icon = models.CharField(max_length=50, default='🍳')
    
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['display_order', 'name']
        unique_together = [['brand', 'code']]
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class KitchenPerformance(models.Model):
    """Daily kitchen performance metrics"""
    brand = models.ForeignKey('core.Brand', on_delete=models.CASCADE, related_name='kitchen_performance')
    station = models.CharField(max_length=20)
    date = models.DateField()
    
    # Metrics
    total_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    avg_prep_time = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # in seconds
    overdue_orders = models.IntegerField(default=0)
    
    # Time tracking
    fastest_time = models.IntegerField(null=True, blank=True)  # in seconds
    slowest_time = models.IntegerField(null=True, blank=True)  # in seconds
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['brand', 'station', 'date']]
        ordering = ['-date', 'station']
    
    def __str__(self):
        return f"{self.station} - {self.date}"
    
    def get_avg_prep_minutes(self):
        """Get average prep time in minutes"""
        if self.avg_prep_time:
            return float(self.avg_prep_time) / 60
        return 0
    
    def get_completion_rate(self):
        """Get completion rate percentage"""
        if self.total_orders > 0:
            return (self.completed_orders / self.total_orders) * 100
        return 0


class PrinterConfig(models.Model):
    """Printer configuration"""
    CONNECTION_TYPES = [
        ('usb', 'USB'),
        ('network', 'Network'),
        ('bluetooth', 'Bluetooth'),
    ]
    
    name = models.CharField(max_length=100)
    brand = models.ForeignKey('core.Brand', on_delete=models.CASCADE, related_name='printers')
    station = models.CharField(max_length=20)
    
    connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    port = models.IntegerField(default=9100)
    usb_vendor = models.CharField(max_length=10, blank=True)
    usb_product = models.CharField(max_length=10, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.station})"


# ============================================================================
# KITCHEN PRINTER SERVICE MODELS
# Based on KITCHEN_PRINTER_PROMPT.md architecture
# ============================================================================

class StationPrinter(models.Model):
    """
    Printer routing configuration for kitchen stations
    Maps printer_target (station_code) to physical printer(s)
    """
    brand = models.ForeignKey('core.Brand', on_delete=models.CASCADE, related_name='station_printers')
    station_code = models.CharField(
        max_length=50, 
        db_index=True,
        help_text='Station code: kitchen, bar, dessert, etc.'
    )
    printer_name = models.CharField(max_length=100, help_text='Friendly name for this printer')
    printer_ip = models.CharField(max_length=255, help_text='IP address or hostname of ESC/POS printer')
    printer_port = models.IntegerField(default=9100, help_text='Printer port (usually 9100)')
    
    # Printer brand and connection type (NEW FIELDS)
    printer_brand = models.CharField(
        max_length=20,
        default='HRPT',
        help_text='Printer brand code: HRPT, EPSON, XPRINTER'
    )
    printer_type = models.CharField(
        max_length=20,
        default='network',
        choices=[
            ('network', 'Network (RAW TCP/IP)'),
            ('win32', 'Windows Driver (Win32Raw)'),
        ],
        help_text='Connection type: network or win32'
    )
    timeout_seconds = models.IntegerField(
        default=5,
        help_text='Network timeout in seconds'
    )
    
    priority = models.IntegerField(
        default=1, 
        help_text='Print priority (1=primary, 2=backup). Lower number = higher priority'
    )
    is_active = models.BooleanField(default=True)
    
    # Printer capabilities
    paper_width_mm = models.IntegerField(default=80, help_text='Paper width in mm (58/80)')
    chars_per_line = models.IntegerField(default=32, help_text='Characters per line')
    
    # Tracking
    last_print_at = models.DateTimeField(null=True, blank=True, help_text='Last successful print')
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_error_message = models.TextField(blank=True)
    total_prints = models.IntegerField(default=0)
    failed_prints = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['station_code', 'priority']
        indexes = [
            models.Index(fields=['station_code', 'is_active', 'priority']),
            models.Index(fields=['brand', 'station_code']),
            models.Index(fields=['printer_brand']),  # NEW INDEX
            models.Index(fields=['printer_type']),   # NEW INDEX
        ]
    
    def __str__(self):
        return f"{self.station_code.upper()} → {self.printer_name} ({self.printer_ip})"
    
    def get_success_rate(self):
        """Calculate print success rate"""
        if self.total_prints == 0:
            return 100.0
        return ((self.total_prints - self.failed_prints) / self.total_prints) * 100


class KitchenTicket(models.Model):
    """
    Print job for kitchen station
    One ticket = one station's portion of an order
    """
    STATUS_CHOICES = [
        ('new', 'New - Waiting to Print'),
        ('printing', 'Printing - In Progress'),
        ('printed', 'Printed - Success'),
        ('failed', 'Failed - Error'),
    ]
    
    bill = models.ForeignKey('pos.Bill', on_delete=models.CASCADE, related_name='kitchen_tickets')
    brand = models.ForeignKey('core.Brand', on_delete=models.PROTECT, null=True, blank=True, db_index=True)
    
    printer_target = models.CharField(
        max_length=50, 
        db_index=True,
        help_text='Target station: kitchen, bar, dessert, etc.'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', db_index=True)
    
    # Retry mechanism
    print_attempts = models.IntegerField(default=0, help_text='Number of print attempts')
    max_retries = models.IntegerField(default=3, help_text='Max retry attempts')
    
    # Printer used
    printer_ip = models.CharField(max_length=255, null=True, blank=True, help_text='Printer that processed this ticket')
    
    # Error tracking
    error_message = models.TextField(blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    printed_at = models.DateTimeField(null=True, blank=True)
    
    # Reprint tracking
    is_reprint = models.BooleanField(default=False, help_text='Is this a reprint request?')
    original_ticket = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reprints'
    )
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['bill', 'printer_target']),
            models.Index(fields=['brand', 'printer_target']),
            models.Index(fields=['printer_target', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Ticket #{self.id} - {self.bill.bill_number} [{self.printer_target.upper()}] - {self.status.upper()}"
    
    def can_retry(self):
        """Check if ticket can be retried"""
        return self.status == 'failed' and self.print_attempts < self.max_retries
    
    def mark_printing(self, printer_ip):
        """Mark ticket as printing"""
        self.status = 'printing'
        self.printer_ip = printer_ip
        self.print_attempts += 1
        self.save(update_fields=['status', 'printer_ip', 'print_attempts'])
    
    def mark_printed(self):
        """Mark ticket as successfully printed"""
        self.status = 'printed'
        self.printed_at = timezone.now()
        self.error_message = ''
        self.save(update_fields=['status', 'printed_at', 'error_message'])
    
    def mark_failed(self, error_message):
        """Mark ticket as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.last_error_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'last_error_at'])


class KitchenTicketItem(models.Model):
    """
    Items in a kitchen ticket
    Links order items to print jobs
    """
    kitchen_ticket = models.ForeignKey(
        KitchenTicket, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    bill_item = models.ForeignKey(
        'pos.BillItem', 
        on_delete=models.CASCADE,
        related_name='kitchen_ticket_items'
    )
    
    quantity = models.IntegerField(help_text='Quantity to print on this ticket')
    
    class Meta:
        indexes = [
            models.Index(fields=['kitchen_ticket', 'bill_item']),
        ]
    
    def __str__(self):
        return f"{self.kitchen_ticket.id} - {self.bill_item.product.name} x{self.quantity}"


class KitchenTicketLog(models.Model):
    """
    Immutable audit trail for all ticket state changes
    CRITICAL for troubleshooting, compliance, and SLA tracking
    """
    ACTION_CHOICES = [
        ('created', 'Ticket Created'),
        ('print_start', 'Print Started'),
        ('print_success', 'Print Success'),
        ('print_failed', 'Print Failed'),
        ('retry', 'Retry Attempt'),
        ('manual_reset', 'Manual Reset'),
        ('marked_printed', 'Manually Marked as Printed'),
        ('marked_failed', 'Manually Marked as Failed'),
    ]
    
    ticket = models.ForeignKey(
        KitchenTicket, 
        on_delete=models.CASCADE, 
        related_name='logs'
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # State change tracking
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    
    # Action context
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    actor = models.CharField(
        max_length=100, 
        help_text='Who/what triggered this: printer_service, admin:username, system'
    )
    
    # Technical details
    printer_ip = models.CharField(max_length=255, null=True, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    duration_ms = models.IntegerField(
        null=True, 
        blank=True,
        help_text='Duration of action in milliseconds'
    )
    
    # Additional context (flexible for future needs)
    metadata = models.JSONField(
        default=dict, 
        blank=True,
        help_text='Additional context: network latency, retry count, etc.'
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ticket', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"Ticket #{self.ticket.id} - {self.action} at {self.timestamp}"
    
    @classmethod
    def log_action(cls, ticket, action, actor, old_status='', new_status='', 
                   printer_ip=None, error_code='', error_message='', 
                   duration_ms=None, metadata=None):
        """
        Convenience method to create log entries
        Usage: KitchenTicketLog.log_action(ticket, 'print_success', 'printer_service', ...)
        """
        return cls.objects.create(
            ticket=ticket,
            action=action,
            actor=actor,
            old_status=old_status or ticket.status,
            new_status=new_status or ticket.status,
            printer_ip=printer_ip,
            error_code=error_code,
            error_message=error_message,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )


class PrinterHealthCheck(models.Model):
    """
    Health monitoring for each printer
    CRITICAL for proactive maintenance and uptime tracking
    """
    PAPER_STATUS_CHOICES = [
        ('ok', 'OK'),
        ('low', 'Low'),
        ('out', 'Out'),
        ('jam', 'Paper Jam'),
        ('unknown', 'Unknown'),
    ]
    
    printer = models.ForeignKey(
        StationPrinter, 
        on_delete=models.CASCADE, 
        related_name='health_checks'
    )
    checked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Connection status
    is_online = models.BooleanField(help_text='Printer responded to ping/connection test')
    response_time_ms = models.IntegerField(
        null=True, 
        blank=True,
        help_text='Response time in milliseconds'
    )
    
    # Paper status (if printer supports status query)
    paper_status = models.CharField(
        max_length=20,
        choices=PAPER_STATUS_CHOICES,
        default='unknown'
    )
    
    # Error details
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    # Additional diagnostics
    temperature_ok = models.BooleanField(null=True, blank=True, help_text='Thermal printer temperature')
    cutter_ok = models.BooleanField(null=True, blank=True, help_text='Auto-cutter status')
    
    class Meta:
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['printer', '-checked_at']),
            models.Index(fields=['-checked_at']),
            models.Index(fields=['is_online', '-checked_at']),
        ]
    
    def __str__(self):
        status = "✅ Online" if self.is_online else "❌ Offline"
        return f"{self.printer.printer_name} - {status} at {self.checked_at}"
    
    @classmethod
    def check_printer(cls, printer):
        """
        Perform health check on a printer
        Returns: (is_online, response_time_ms, error_message)
        """
        import socket
        import time
        
        start_time = time.time()
        is_online = False
        response_time_ms = None
        error_message = ''
        
        try:
            # Simple TCP connection test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 second timeout
            result = sock.connect_ex((str(printer.printer_ip), printer.printer_port))
            sock.close()
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if result == 0:
                is_online = True
            else:
                error_message = f'Connection failed with code {result}'
                
        except socket.timeout:
            error_message = 'Connection timeout'
        except Exception as e:
            error_message = str(e)
        
        # Create health check record
        health_check = cls.objects.create(
            printer=printer,
            is_online=is_online,
            response_time_ms=response_time_ms,
            error_message=error_message
        )
        
        return health_check
    
    def is_healthy(self):
        """Quick check if printer is in good state"""
        return (
            self.is_online and 
            self.paper_status in ['ok', 'low', 'unknown'] and
            not self.error_message
        )
