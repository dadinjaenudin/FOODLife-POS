from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid

# Import refund models
from .models_refund import BillRefund, BillRefundItem, RefundPaymentReversal


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
    
    # Multi-Tenant Hierarchy (DENORMALIZED for production performance)
    company = models.ForeignKey('core.Company', on_delete=models.PROTECT, related_name='bills', null=True, blank=True, help_text="Denormalized for reporting performance")
    brand = models.ForeignKey('core.Brand', on_delete=models.PROTECT, related_name='bills')
    store = models.ForeignKey('core.Store', on_delete=models.PROTECT, related_name='bills', null=True)
    
    table = models.ForeignKey('tables.Table', on_delete=models.SET_NULL, null=True, blank=True, related_name='bills')
    terminal = models.ForeignKey('core.POSTerminal', on_delete=models.SET_NULL, null=True, blank=True, related_name='bills')
    
    # Member tracking from external CRM (no ForeignKey)
    member_code = models.CharField(max_length=50, blank=True, help_text='Member ID/Code from external CRM')
    member_name = models.CharField(max_length=200, blank=True, help_text='Member name for display')
    
    bill_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='dine_in')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    guest_count = models.IntegerField(default=1)
    queue_number = models.IntegerField(null=True, blank=True, help_text='Auto-increment daily for takeaway orders')
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Line Item Discounts (from individual items)
    line_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Subtotal/Bill Level Discounts
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_type = models.CharField(max_length=20, blank=True)  # manual, voucher, member, promotion
    discount_reference = models.CharField(max_length=100, blank=True)  # voucher code, promotion name
    
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_by = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='bills_created')
    created_at = models.DateTimeField(auto_now_add=True)
    closed_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='bills_closed')
    closed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True, help_text='When order was picked up by customer')
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Primary reporting index (company-level)
            models.Index(fields=['company', 'created_at']),  # Finance/HO reports
            models.Index(fields=['company', 'status', 'created_at']),  # Company-wide analytics
            
            # Brand/Store level
            models.Index(fields=['brand', 'store', 'status', 'created_at']),
            models.Index(fields=['store', 'created_at']),
            
            # Operational
            models.Index(fields=['table', 'status']),
            models.Index(fields=['member_code', 'created_at']),  # Member code from external CRM
            models.Index(fields=['brand', 'bill_type', 'created_at']),  # Queue lookup
            models.Index(fields=['created_by', 'created_at']),  # For cashier reports
            models.Index(fields=['closed_by', 'closed_at']),    # For cashier reports
        ]
    
    def __str__(self):
        if self.bill_type == 'takeaway' and self.queue_number:
            return f"Queue #{self.queue_number} - {self.bill_number}"
        elif self.bill_type == 'dine_in' and self.table:
            return f"Table {self.table.number} - {self.bill_number}"
        return self.bill_number
    
    def get_display_identifier(self):
        """Get human-readable identifier for display"""
        if self.bill_type == 'takeaway' and self.queue_number:
            return f"Queue #{self.queue_number}"
        elif self.table:
            return f"Table {self.table.number}"
        return self.bill_number
    
    def mark_completed(self, user):
        """Mark bill as completed (customer picked up order)"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Log action
        BillLog.objects.create(
            bill=self,
            action='completed',
            details={'completed_by': user.username, 'queue_number': self.queue_number},
            user=user
        )
    
    def save(self, *args, **kwargs):
        if not self.bill_number:
            self.bill_number = self.generate_bill_number()
        super().save(*args, **kwargs)
    
    def generate_bill_number(self):
        today = timezone.now().strftime('%Y%m%d')
        # Use brand code instead of ID for UUID compatibility
        brand_code = self.brand.code if hasattr(self.brand, 'code') else '001'
        prefix = f"{brand_code}-{today}"
        last_bill = Bill.objects.filter(bill_number__startswith=prefix).order_by('-bill_number').first()
        if last_bill:
            last_num = int(last_bill.bill_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        return f"{prefix}-{new_num:04d}"
    
    def calculate_totals(self):
        # Calculate subtotal from items
        self.subtotal = sum(item.total for item in self.items.filter(is_void=False))
        
        # Calculate line item discounts (from individual item discounts)
        self.line_discount_amount = sum(item.discount_amount for item in self.items.filter(is_void=False) if hasattr(item, 'discount_amount'))
        
        # Calculate subtotal/bill level discount
        if self.discount_percent > 0:
            self.discount_amount = self.subtotal * (self.discount_percent / 100)
        
        # After all discounts
        after_discount = self.subtotal - self.line_discount_amount - self.discount_amount
        
        # Safely get tax and service charge rates
        tax_rate = self.brand.tax_rate if self.brand else Decimal('0')
        service_charge_rate = self.brand.service_charge if self.brand else Decimal('0')
        
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
    
    # Denormalized for analytics (optional but recommended)
    company = models.ForeignKey('core.Company', on_delete=models.PROTECT, null=True, blank=True, help_text="Denormalized for product analytics")
    brand = models.ForeignKey('core.Brand', on_delete=models.PROTECT, null=True, blank=True, help_text="Denormalized for product analytics")
    
    product = models.ForeignKey('core.Product', on_delete=models.PROTECT)
    
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    modifier_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    modifiers = models.JSONField(default=list, blank=True)
    
    # Kitchen printer routing
    printer_target = models.CharField(
        max_length=50, 
        blank=True, 
        help_text='Kitchen station code for printer routing (e.g., BAR, KITCHEN, DESSERT)'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_void = models.BooleanField(default=False)
    void_reason = models.TextField(blank=True)
    void_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='voided_items')
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='bill_items_created')
    
    split_group = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['bill', 'is_void', 'status']),
            models.Index(fields=['created_by', 'created_at']),  # For cashier item reports
            # Product analytics indexes
            models.Index(fields=['company', 'product', 'created_at']),  # Company-wide product sales
            models.Index(fields=['brand', 'product', 'created_at']),    # Brand-level product mix
        ]
    
    def save(self, *args, **kwargs):
        self.total = (self.unit_price + self.modifier_price) * self.quantity
        super().save(*args, **kwargs)


class Payment(models.Model):
    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('debit', 'Debit Card'),
        ('qris', 'QRIS'),
        ('transfer', 'Bank Transfer'),
        ('ewallet', 'E-Wallet'),
        ('voucher', 'Voucher'),
    ]

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    method = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)

    payment_profile = models.ForeignKey(
        'core.PaymentMethodProfile', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='payments',
        help_text='Payment method profile used (null for legacy payments)'
    )
    payment_metadata = models.JSONField(
        default=dict, blank=True,
        help_text='Extra data fields from prompts: {"account_no": "1234", "eft_no": "AB"}'
    )
    eft_desc = models.CharField(
        max_length=120, blank=True,
        help_text='Denormalized EFT terminal description, e.g. "01: BCA"'
    )

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
        ('completed', 'Order Completed'),
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


class PrintJob(models.Model):
    """
    Print job queue for remote printing via Print Agent
    Production-ready with idempotent processing
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('fetched', 'Fetched'),
        ('printing', 'Printing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    JOB_TYPE_CHOICES = [
        ('receipt', 'Customer Receipt'),
        ('kitchen', 'Kitchen Order'),
        ('report', 'Report'),
        ('reprint', 'Reprint'),
    ]
    
    # Unique identifier for idempotent processing
    job_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    terminal_id = models.CharField(max_length=50, help_text='Target terminal/cashier ID')
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='print_jobs', null=True, blank=True)
    
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    content = models.JSONField(help_text='Print job data (bill info, items, etc)')
    
    # Lifecycle tracking
    fetched_at = models.DateTimeField(null=True, blank=True, help_text='When agent picked up the job')
    
    # Error handling
    retry_count = models.IntegerField(default=0)
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['terminal_id', 'status', 'created_at']),
            models.Index(fields=['job_uuid']),
        ]
    
    def __str__(self):
        return f"PrintJob #{self.id} - {self.job_type} for {self.terminal_id}"


class QRISTransaction(models.Model):
    """Tracks QRIS payment lifecycle (pending → paid/expired/cancelled)."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='qris_transactions')
    transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    qr_string = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    gateway_name = models.CharField(max_length=50, default='mock')
    gateway_response = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='qris_transactions'
    )

    class Meta:
        db_table = 'pos_qris_transaction'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['bill', 'status']),
            models.Index(fields=['transaction_id']),
        ]

    def __str__(self):
        return f"QRIS {self.transaction_id} - {self.status} - Rp{self.amount}"


class QRISAuditLog(models.Model):
    """
    Detailed audit log for every QRIS event — for bank analysis & reconciliation.

    Captures: create, status_check, status_change, payment_confirmed, expired,
    cancelled, simulate, error, auto_cancel, gateway_timeout, etc.

    Each row = 1 event with response_time_ms for performance analysis.
    """
    EVENT_CHOICES = [
        ('create', 'QR Created'),
        ('status_check', 'Status Polled'),
        ('status_change', 'Status Changed'),
        ('payment_confirmed', 'Payment Confirmed'),
        ('expired', 'Transaction Expired'),
        ('cancelled', 'Transaction Cancelled'),
        ('auto_cancel', 'Auto-cancelled (new QR)'),
        ('simulate', 'Payment Simulated'),
        ('error', 'Error'),
        ('gateway_timeout', 'Gateway Timeout'),
        ('gateway_error', 'Gateway Error'),
    ]

    id = models.BigAutoField(primary_key=True)
    transaction = models.ForeignKey(
        QRISTransaction, on_delete=models.CASCADE,
        related_name='audit_logs', null=True, blank=True,
    )
    bill = models.ForeignKey(
        Bill, on_delete=models.CASCADE,
        related_name='qris_audit_logs', null=True, blank=True,
    )
    event = models.CharField(max_length=30, choices=EVENT_CHOICES)
    txn_ref = models.CharField(max_length=100, blank=True, db_index=True, help_text='QRIS transaction_id reference')
    status_before = models.CharField(max_length=20, blank=True)
    status_after = models.CharField(max_length=20, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    gateway_name = models.CharField(max_length=50, blank=True)
    response_time_ms = models.IntegerField(
        null=True, blank=True,
        help_text='Response time from gateway in milliseconds',
    )
    elapsed_since_create_s = models.FloatField(
        null=True, blank=True,
        help_text='Seconds since QR was created (wait time)',
    )
    error_message = models.TextField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'pos_qris_audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['txn_ref', 'event']),
            models.Index(fields=['bill', 'created_at']),
            models.Index(fields=['event', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.event}] {self.txn_ref} @ {self.created_at}"


class StoreProductStock(models.Model):
    """
    Store-level product stock management (independent from HO sync).

    IMPORTANT DESIGN DECISIONS:
    - NO FK constraint to core.Product because core_product table may be
      delete+inserted daily during HO sync, which would break FK references.
    - Uses product_sku + brand as stable identifier for matching products.
    - Only products in this table are stock-tracked.
      Products NOT in this table are considered ALWAYS AVAILABLE.
    - daily_stock = opening stock set by store staff each day.
    - sold_qty = incremented when items are sent to kitchen.
    - remaining = daily_stock - sold_qty (computed property).

    DAILY WORKFLOW:
    1. Store staff sets daily_stock for each tracked product (morning)
    2. When cashier sends items to kitchen, sold_qty increases
    3. When items are voided, sold_qty decreases (restore)
    4. Product card shows "Out of Stock" when remaining <= 0
    5. Next day, staff resets sold_qty and sets new daily_stock
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Product reference - NO FK constraint (HO sync may delete+insert core_product)
    # product_id stored for quick lookup, product_sku+brand for stable matching
    product_id = models.UUIDField(
        db_index=True,
        help_text='Reference to core_product.id (not FK - may change on sync)'
    )
    product_sku = models.CharField(max_length=50, db_index=True, help_text='SKU from core_product')
    product_name = models.CharField(max_length=200, help_text='Cached product name for display')
    brand = models.ForeignKey(
        'core.Brand', on_delete=models.CASCADE, related_name='store_stocks',
        help_text='Brand this stock record belongs to'
    )

    # Stock management
    daily_stock = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Opening stock for the day (set by store staff)'
    )
    sold_qty = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Quantity sold/sent to kitchen today'
    )

    # Settings
    low_stock_alert = models.IntegerField(
        default=5,
        help_text='Show warning when remaining stock falls below this number'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this product is being stock-tracked'
    )

    # Tracking
    last_reset_date = models.DateField(
        null=True, blank=True,
        help_text='Last date stock was reset/restocked'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pos_store_product_stock'
        verbose_name = 'Store Product Stock'
        verbose_name_plural = 'Store Product Stocks'
        unique_together = [['product_sku', 'brand']]
        ordering = ['product_name']
        indexes = [
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['product_id']),
        ]

    @property
    def remaining_stock(self):
        """Calculate remaining stock: opening - sold"""
        return self.daily_stock - self.sold_qty

    @property
    def is_out_of_stock(self):
        """True if no stock remaining"""
        return self.remaining_stock <= 0

    @property
    def is_low_stock(self):
        """True if stock is low but not zero"""
        remaining = self.remaining_stock
        return 0 < remaining <= self.low_stock_alert

    def deduct_stock(self, qty):
        """Deduct stock when items sent to kitchen"""
        from decimal import Decimal
        self.sold_qty += Decimal(str(qty))
        self.save(update_fields=['sold_qty', 'updated_at'])

    def restore_stock(self, qty):
        """Restore stock when items are voided"""
        from decimal import Decimal
        self.sold_qty = max(Decimal('0'), self.sold_qty - Decimal(str(qty)))
        self.save(update_fields=['sold_qty', 'updated_at'])

    def reset_daily(self, new_stock=None):
        """Reset stock for new day"""
        from decimal import Decimal
        if new_stock is not None:
            self.daily_stock = Decimal(str(new_stock))
        self.sold_qty = Decimal('0')
        self.last_reset_date = timezone.now().date()
        self.save(update_fields=['daily_stock', 'sold_qty', 'last_reset_date', 'updated_at'])

    def sync_product_id(self):
        """
        Re-match product_id after HO sync (in case UUID changed).
        Call this after daily sync to update product_id reference.
        """
        from apps.core.models import Product
        product = Product.objects.filter(sku=self.product_sku, brand=self.brand).first()
        if product and str(product.id) != str(self.product_id):
            self.product_id = product.id
            self.product_name = product.name
            self.save(update_fields=['product_id', 'product_name', 'updated_at'])
            return True
        return False

    def __str__(self):
        remaining = self.remaining_stock
        return f"{self.product_name} [{self.product_sku}] - Stock: {remaining}/{self.daily_stock}"

