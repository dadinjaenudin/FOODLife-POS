from django.db import models
from django.utils import timezone
from datetime import timedelta


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
