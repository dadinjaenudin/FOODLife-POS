from django.db import models


class KitchenOrder(models.Model):
    """Aggregated view for KDS"""
    STATUS_CHOICES = [
        ('new', 'New'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
    ]
    
    bill = models.ForeignKey('pos.Bill', on_delete=models.CASCADE, related_name='kitchen_orders')
    station = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.bill.bill_number} - {self.station}"


class PrinterConfig(models.Model):
    """Printer configuration"""
    CONNECTION_TYPES = [
        ('usb', 'USB'),
        ('network', 'Network'),
        ('bluetooth', 'Bluetooth'),
    ]
    
    name = models.CharField(max_length=100)
    outlet = models.ForeignKey('core.Outlet', on_delete=models.CASCADE, related_name='printers')
    station = models.CharField(max_length=20)
    
    connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    port = models.IntegerField(default=9100)
    usb_vendor = models.CharField(max_length=10, blank=True)
    usb_product = models.CharField(max_length=10, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.station})"
