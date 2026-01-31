from django.db import models
from django.utils import timezone
from decimal import Decimal


class BillRefund(models.Model):
    """
    Refund tracking for paid bills (CRITICAL for F&B operations)
    
    Handles:
    - Full refunds (entire bill)
    - Partial refunds (some items)
    - Wrong order / Customer complaint
    - Payment reversal tracking
    """
    
    REFUND_TYPE_CHOICES = [
        ('full', 'Full Refund'),
        ('partial', 'Partial Refund'),
    ]
    
    REASON_CHOICES = [
        ('wrong_order', 'Wrong Order / Input Error'),
        ('customer_complaint', 'Customer Complaint'),
        ('quality_issue', 'Quality Issue'),
        ('service_issue', 'Service Issue'),
        ('price_error', 'Price Error'),
        ('duplicate_payment', 'Duplicate Payment'),
        ('cancelled_late', 'Cancelled After Payment'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    # Core Fields
    refund_number = models.CharField(max_length=50, unique=True, blank=True)
    original_bill = models.ForeignKey('pos.Bill', on_delete=models.PROTECT, related_name='refunds')
    
    refund_type = models.CharField(max_length=20, choices=REFUND_TYPE_CHOICES)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    reason_notes = models.TextField(blank=True, help_text="Detailed explanation")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Financial Tracking
    original_total = models.DecimalField(max_digits=12, decimal_places=2, help_text="Original bill total")
    refund_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_service_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Approval Workflow
    requested_by = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='refunds_requested')
    requested_at = models.DateTimeField(auto_now_add=True)
    
    approved_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='refunds_approved')
    approval_pin = models.CharField(max_length=6, blank=True)
    approval_notes = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Completion
    completed_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='refunds_completed')
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Payment Reversal Tracking
    original_payments = models.JSONField(default=dict, help_text="Original payment methods and amounts")
    refund_payments = models.JSONField(default=dict, help_text="How refund was processed per payment method")
    
    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['original_bill', 'status']),
            models.Index(fields=['refund_number']),
            models.Index(fields=['status', 'requested_at']),
            models.Index(fields=['requested_by', 'requested_at']),
        ]
    
    def __str__(self):
        return f"{self.refund_number} - {self.original_bill.bill_number}"
    
    def save(self, *args, **kwargs):
        if not self.refund_number:
            self.refund_number = self.generate_refund_number()
        super().save(*args, **kwargs)
    
    def generate_refund_number(self):
        """Generate unique refund number: RF-BRANDCODE-YYYYMMDD-XXX"""
        today = timezone.now().strftime('%Y%m%d')
        brand_code = self.original_bill.brand.code if self.original_bill.brand else '001'
        prefix = f"RF-{brand_code}-{today}"
        
        last_refund = BillRefund.objects.filter(refund_number__startswith=prefix).order_by('-refund_number').first()
        if last_refund:
            last_num = int(last_refund.refund_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}-{new_num:03d}"
    
    def calculate_refund_totals(self):
        """Calculate refund totals based on refunded items"""
        if self.refund_type == 'full':
            # Full refund = entire bill
            self.refund_subtotal = self.original_bill.subtotal - self.original_bill.line_discount_amount - self.original_bill.discount_amount
            self.refund_tax = self.original_bill.tax_amount
            self.refund_service_charge = self.original_bill.service_charge
            self.refund_total = self.original_bill.total
        else:
            # Partial refund = sum of refunded items
            refunded_items = self.refunded_items.all()
            subtotal = sum(
                item.original_item.unit_price * item.refund_quantity 
                for item in refunded_items
            )
            
            # Proportional tax and service charge
            if self.original_bill.subtotal > 0:
                ratio = subtotal / self.original_bill.subtotal
                self.refund_tax = self.original_bill.tax_amount * ratio
                self.refund_service_charge = self.original_bill.service_charge * ratio
            
            self.refund_subtotal = subtotal
            self.refund_total = self.refund_subtotal + self.refund_tax + self.refund_service_charge
        
        self.save()
    
    def approve(self, user, pin, notes=''):
        """Approve refund request"""
        if self.status != 'pending':
            return False, "Refund tidak dalam status pending"
        
        # Validate user authority (could add role_scope check here)
        if user.role not in ['admin', 'manager']:
            return False, "User tidak memiliki hak approval"
        
        self.status = 'approved'
        self.approved_by = user
        self.approval_pin = pin
        self.approval_notes = notes
        self.approved_at = timezone.now()
        self.save()
        
        return True, "Refund approved"
    
    def reject(self, user, notes=''):
        """Reject refund request"""
        if self.status != 'pending':
            return False, "Refund tidak dalam status pending"
        
        if user.role not in ['admin', 'manager']:
            return False, "User tidak memiliki hak rejection"
        
        self.status = 'rejected'
        self.approved_by = user
        self.approval_notes = notes
        self.approved_at = timezone.now()
        self.save()
        
        return True, "Refund rejected"
    
    def complete(self, user, payment_details):
        """Complete refund after money returned"""
        if self.status != 'approved':
            return False, "Refund belum approved"
        
        self.status = 'completed'
        self.completed_by = user
        self.completed_at = timezone.now()
        self.refund_payments = payment_details
        self.save()
        
        return True, "Refund completed"


class BillRefundItem(models.Model):
    """
    Items being refunded in partial refund
    
    Tracks:
    - Which items from original bill
    - How many units refunded (can be less than original)
    - Reason per item
    """
    
    refund = models.ForeignKey(BillRefund, on_delete=models.CASCADE, related_name='refunded_items')
    original_item = models.ForeignKey('pos.BillItem', on_delete=models.PROTECT)
    
    original_quantity = models.IntegerField()
    refund_quantity = models.IntegerField()
    refund_reason = models.CharField(max_length=100, blank=True)
    
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        indexes = [
            models.Index(fields=['refund', 'original_item']),
        ]
    
    def __str__(self):
        return f"{self.refund.refund_number} - {self.original_item.product.name} x{self.refund_quantity}"
    
    def save(self, *args, **kwargs):
        # Calculate refund amount
        self.unit_price = self.original_item.unit_price + self.original_item.modifier_price
        self.refund_amount = self.unit_price * self.refund_quantity
        super().save(*args, **kwargs)


class RefundPaymentReversal(models.Model):
    """
    Track payment reversals for reconciliation
    
    When customer paid with multiple methods:
    - Cash 50k
    - Card 100k
    
    Refund must reverse correctly:
    - Cash 50k back
    - Card 100k back
    """
    
    refund = models.ForeignKey(BillRefund, on_delete=models.CASCADE, related_name='payment_reversals')
    original_payment = models.ForeignKey('pos.Payment', on_delete=models.PROTECT, null=True, blank=True)
    
    payment_method = models.CharField(max_length=20)
    original_amount = models.DecimalField(max_digits=12, decimal_places=2)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    reference = models.CharField(max_length=100, blank=True, help_text="Refund transaction reference")
    notes = models.TextField(blank=True)
    
    processed_by = models.ForeignKey('core.User', on_delete=models.PROTECT)
    processed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['refund', 'payment_method']),
            models.Index(fields=['original_payment']),
        ]
    
    def __str__(self):
        return f"{self.refund.refund_number} - {self.payment_method} - {self.refund_amount}"
