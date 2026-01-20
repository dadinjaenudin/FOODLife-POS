from django.db import models
from django.utils import timezone
from decimal import Decimal


class Bill(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('hold', 'On Hold'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
        ('void', 'Voided'),
    ]
    
    TYPE_CHOICES = [
        ('dine_in', 'Dine In'),
        ('takeaway', 'Take Away'),
        ('delivery', 'Delivery'),
    ]
    
    bill_number = models.CharField(max_length=50, unique=True, blank=True)
    outlet = models.ForeignKey('core.Outlet', on_delete=models.PROTECT, related_name='bills')
    table = models.ForeignKey('tables.Table', on_delete=models.SET_NULL, null=True, blank=True, related_name='bills')
    terminal = models.ForeignKey('core.POSTerminal', on_delete=models.SET_NULL, null=True, blank=True, related_name='bills')
    
    bill_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='dine_in')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    guest_count = models.IntegerField(default=1)
    queue_number = models.IntegerField(null=True, blank=True)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_by = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='bills_created')
    created_at = models.DateTimeField(auto_now_add=True)
    closed_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='bills_closed')
    closed_at = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['outlet', 'status', 'created_at']),
            models.Index(fields=['table', 'status']),
            models.Index(fields=['created_by', 'created_at']),  # For cashier reports
            models.Index(fields=['closed_by', 'closed_at']),    # For cashier reports
        ]
    
    def __str__(self):
        return self.bill_number
    
    def save(self, *args, **kwargs):
        if not self.bill_number:
            self.bill_number = self.generate_bill_number()
        super().save(*args, **kwargs)
    
    def generate_bill_number(self):
        today = timezone.now().strftime('%Y%m%d')
        # Use outlet code instead of ID for UUID compatibility
        outlet_code = self.outlet.code if hasattr(self.outlet, 'code') else '001'
        prefix = f"{outlet_code}-{today}"
        last_bill = Bill.objects.filter(bill_number__startswith=prefix).order_by('-bill_number').first()
        if last_bill:
            last_num = int(last_bill.bill_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        return f"{prefix}-{new_num:04d}"
    
    def calculate_totals(self):
        self.subtotal = sum(item.total for item in self.items.filter(is_void=False))
        
        if self.discount_percent > 0:
            self.discount_amount = self.subtotal * (self.discount_percent / 100)
        
        after_discount = self.subtotal - self.discount_amount
        
        # Safely get tax and service charge rates
        tax_rate = self.outlet.tax_rate if self.outlet else Decimal('0')
        service_charge_rate = self.outlet.service_charge if self.outlet else Decimal('0')
        
        self.tax_amount = after_discount * (tax_rate / 100)
        self.service_charge = after_discount * (service_charge_rate / 100)
        
        self.total = after_discount + self.tax_amount + self.service_charge
        self.save()
    
    def get_paid_amount(self):
        return sum(p.amount for p in self.payments.all())
    
    def get_remaining(self):
        return self.total - self.get_paid_amount()


class BillItem(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent to Kitchen'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
    ]
    
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('core.Product', on_delete=models.PROTECT)
    
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    modifier_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    modifiers = models.JSONField(default=list, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_void = models.BooleanField(default=False)
    void_reason = models.TextField(blank=True)
    void_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='voided_items')
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='bill_items_created')
    
    split_group = models.IntegerField(default=0)
    
    class Meta:
        indexes = [
            models.Index(fields=['bill', 'is_void', 'status']),
            models.Index(fields=['created_by', 'created_at']),  # For cashier item reports
        ]
    
    def save(self, *args, **kwargs):
        self.total = (self.unit_price + self.modifier_price) * self.quantity
        super().save(*args, **kwargs)


class Payment(models.Model):
    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('qris', 'QRIS'),
        ('transfer', 'Bank Transfer'),
        ('ewallet', 'E-Wallet'),
        ('voucher', 'Voucher'),
    ]
    
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='payments_processed')
    
    class Meta:
        indexes = [
            models.Index(fields=['bill', 'created_at']),
            models.Index(fields=['created_by', 'created_at']),  # For cashier payment reports
        ]
    
    def __str__(self):
        return f"{self.bill.bill_number} - {self.method} - {self.amount}"


class BillLog(models.Model):
    """Audit log for bill activities"""
    ACTION_CHOICES = [
        ('open', 'Bill Opened'),
        ('add_item', 'Item Added'),
        ('void_item', 'Item Voided'),
        ('update_qty', 'Quantity Updated'),
        ('hold', 'Bill Held'),
        ('resume', 'Bill Resumed'),
        ('send_kitchen', 'Sent to Kitchen'),
        ('payment', 'Payment Made'),
        ('close', 'Bill Closed'),
        ('cancel', 'Bill Cancelled'),
        ('discount', 'Discount Applied'),
        ('reprint_receipt', 'Receipt Reprinted'),
        ('reprint_kitchen', 'Kitchen Order Reprinted'),
        ('split_bill', 'Bill Split'),
        ('merge_bill', 'Bill Merged'),
        ('move_table', 'Table Moved'),
    ]
    
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict, blank=True)
    
    user = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
