"""
Business Date & Store Session Management Models

Handles:
- EOD (End of Day) process
- Business date vs calendar date
- Cashier shift management
- Cash reconciliation
"""
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid


class StoreSession(models.Model):
    """
    Store session represents a business day
    One session = one business date (regardless of calendar date)
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('force_closed', 'Force Closed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('Store', on_delete=models.PROTECT, related_name='sessions')
    business_date = models.DateField()
    session_number = models.IntegerField(default=1)
    
    opened_at = models.DateTimeField(default=timezone.now)
    opened_by = models.ForeignKey('User', on_delete=models.PROTECT, related_name='sessions_opened')
    
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions_closed')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    is_current = models.BooleanField(default=False)
    
    settings = models.JSONField(default=dict, blank=True)
    eod_notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = [['store', 'business_date', 'session_number']]
        indexes = [
            models.Index(fields=['store', 'is_current']),
            models.Index(fields=['store', 'business_date']),
            models.Index(fields=['status', 'opened_at']),
        ]
        ordering = ['-business_date', '-session_number']
    
    def __str__(self):
        return f"{self.store.store_code} - {self.business_date} (Session {self.session_number})"
    
    def clean(self):
        # Ensure only one current session per store
        if self.is_current:
            existing = StoreSession.objects.filter(
                store=self.store,
                is_current=True
            ).exclude(id=self.id)
            if existing.exists():
                raise ValidationError("Another session is already active for this store")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_current(cls, store):
        """Get current active session for store"""
        try:
            return cls.objects.get(store=store, is_current=True)
        except cls.DoesNotExist:
            return None
    
    def hours_since_open(self):
        """Hours since session opened"""
        delta = timezone.now() - self.opened_at
        return delta.total_seconds() / 3600
    
    def is_overdue(self, threshold_hours=24):
        """Check if session is overdue for EOD"""
        return self.status == 'open' and self.hours_since_open() > threshold_hours
    
    def close(self, closed_by, notes='', force=False):
        """Close current session and create next session"""
        if self.status != 'open':
            raise ValidationError("Session is already closed")
        
        # Check all shifts are closed
        open_shifts = self.shifts.filter(status='open')
        if open_shifts.exists() and not force:
            raise ValidationError(f"{open_shifts.count()} shift(s) still open. Close them first or use force=True")
        
        # Close this session
        self.closed_at = timezone.now()
        self.closed_by = closed_by
        self.status = 'force_closed' if force else 'closed'
        self.eod_notes = notes
        self.is_current = False
        self.save()
        
        # Create next session
        next_business_date = self.business_date + timezone.timedelta(days=1)
        next_session = StoreSession.objects.create(
            store=self.store,
            business_date=next_business_date,
            session_number=1,
            opened_by=closed_by,
            is_current=True,
        )
        
        return next_session


class CashierShift(models.Model):
    """
    Individual cashier shift within a session
    Tracks cash reconciliation
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('abandoned', 'Abandoned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Multi-tenant fields (complete hierarchy)
    company = models.ForeignKey('Company', on_delete=models.PROTECT, related_name='cashier_shifts', null=True, blank=True)
    brand = models.ForeignKey('Brand', on_delete=models.PROTECT, related_name='cashier_shifts', null=True, blank=True)
    store = models.ForeignKey('Store', on_delete=models.PROTECT, related_name='cashier_shifts', null=True, blank=True)

    store_session = models.ForeignKey(StoreSession, on_delete=models.PROTECT, related_name='shifts')
    cashier = models.ForeignKey('User', on_delete=models.PROTECT, related_name='cashier_shifts')
    terminal = models.ForeignKey('POSTerminal', on_delete=models.PROTECT, related_name='shifts')
    
    shift_start = models.DateTimeField(default=timezone.now)
    shift_end = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    opening_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expected_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_cash = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cash_difference = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    closed_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='shifts_closed')
    notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['company', 'brand', 'store']),
            models.Index(fields=['store_session', 'cashier']),
            models.Index(fields=['cashier', 'shift_start']),
            models.Index(fields=['terminal', 'status']),
        ]
        ordering = ['-shift_start']
    
    def __str__(self):
        return f"{self.cashier.username} - {self.shift_start.strftime('%Y-%m-%d %H:%M')}"
    
    def get_expected_cash(self):
        """Calculate expected cash from cash payments"""
        from apps.pos.models import Payment

        cash_payments = Payment.objects.filter(
            bill__created_by=self.cashier,
            bill__created_at__gte=self.shift_start,
            bill__status='paid',
            method='cash'
        ).aggregate(models.Sum('amount'))

        total_cash = cash_payments['amount__sum'] or Decimal('0')
        return self.opening_cash + total_cash
    
    def get_bills_count(self):
        """Get number of bills in this shift"""
        from apps.pos.models import Bill
        return Bill.objects.filter(
            created_by=self.cashier,
            created_at__gte=self.shift_start
        ).count()
    
    def get_total_sales(self):
        """Get total sales amount in this shift"""
        from apps.pos.models import Bill
        return Bill.objects.filter(
            created_by=self.cashier,
            created_at__gte=self.shift_start,
            status='paid'
        ).aggregate(
            models.Sum('total')
        )['total__sum'] or Decimal('0')
    
    def hours_since_open(self):
        """Hours since shift started"""
        delta = timezone.now() - self.shift_start
        return delta.total_seconds() / 3600
    
    def close_shift(self, actual_cash, closed_by, notes=''):
        """Close shift with cash reconciliation"""
        if self.status != 'open':
            raise ValidationError("Shift is already closed")
        
        self.shift_end = timezone.now()
        self.expected_cash = self.get_expected_cash()
        self.actual_cash = actual_cash
        self.cash_difference = actual_cash - self.expected_cash
        self.closed_by = closed_by
        self.notes = notes
        self.status = 'closed'
        self.save()
        
        return self.cash_difference


class ShiftPaymentSummary(models.Model):
    """
    Payment method breakdown for shift reconciliation
    """
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('debit', 'Debit Card'),
        ('qris', 'QRIS'),
        ('transfer', 'Bank Transfer'),
        ('ewallet', 'E-Wallet'),
        ('voucher', 'Voucher'),
        ('deposit', 'Deposit (Reservation)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cashier_shift = models.ForeignKey(CashierShift, on_delete=models.CASCADE, related_name='payment_summaries')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    difference = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transaction_count = models.IntegerField(default=0)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = [['cashier_shift', 'payment_method']]
        ordering = ['payment_method']
    
    def __str__(self):
        return f"{self.cashier_shift} - {self.payment_method}"
    
    def calculate_expected(self):
        """Calculate expected amount from payments"""
        from apps.pos.models import Payment

        # Get the cashier user instance
        cashier = self.cashier_shift.cashier
        shift_start = self.cashier_shift.shift_start

        # Use created_at to scope bills to this shift only
        payments = Payment.objects.filter(
            bill__created_by=cashier,
            bill__created_at__gte=shift_start,
            bill__status='paid',
            method=self.payment_method
        ).aggregate(
            total=models.Sum('amount'),
            count=models.Count('id')
        )
        
        self.expected_amount = payments['total'] or Decimal('0')
        self.transaction_count = payments['count'] or 0
        self.difference = self.actual_amount - self.expected_amount
        self.save()


class EODChecklist(models.Model):
    """
    EOD checklist items that must be completed
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_session = models.ForeignKey(StoreSession, on_delete=models.CASCADE, related_name='checklist_items')
    
    checklist_item = models.CharField(max_length=200)
    is_completed = models.BooleanField(default=False)
    
    completed_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['checklist_item']
    
    def __str__(self):
        status = "✅" if self.is_completed else "⏳"
        return f"{status} {self.checklist_item}"
    
    def complete(self, user, notes=''):
        """Mark checklist item as completed"""
        self.is_completed = True
        self.completed_by = user
        self.completed_at = timezone.now()
        self.notes = notes
        self.save()


class BusinessDateAlert(models.Model):
    """
    System alerts for business date anomalies
    """
    ALERT_TYPES = [
        ('eod_overdue', 'EOD Overdue'),
        ('shift_overtime', 'Shift Overtime'),
        ('cash_variance', 'Cash Variance'),
        ('session_anomaly', 'Session Anomaly'),
    ]
    
    SEVERITY_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey('Store', on_delete=models.CASCADE, related_name='alerts')
    
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='warning')
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['store', 'acknowledged', 'severity']),
            models.Index(fields=['alert_type', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"[{self.severity.upper()}] {self.alert_type} - {self.message[:50]}"
    
    def acknowledge(self, user):
        """Acknowledge alert"""
        self.acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()
    
    @classmethod
    def create_eod_overdue_alert(cls, store, session):
        """Create EOD overdue alert"""
        hours = session.hours_since_open()
        severity = 'critical' if hours > 24 else 'warning'
        
        return cls.objects.create(
            store=store,
            alert_type='eod_overdue',
            severity=severity,
            message=f"EOD overdue for {hours:.1f} hours. Business date: {session.business_date}",
            data={
                'session_id': str(session.id),
                'business_date': str(session.business_date),
                'hours_overdue': hours,
            }
        )
    
    @classmethod
    def create_cash_variance_alert(cls, store, shift):
        """Create cash variance alert"""
        variance_amount = abs(shift.cash_difference)
        threshold = Decimal('50000')  # Rp 50,000
        
        if variance_amount < threshold:
            return None
        
        severity = 'critical' if variance_amount > threshold * 2 else 'warning'
        
        return cls.objects.create(
            store=store,
            alert_type='cash_variance',
            severity=severity,
            message=f"Cash variance Rp {variance_amount:,.0f} for {shift.cashier.username}",
            data={
                'shift_id': str(shift.id),
                'cashier_id': str(shift.cashier.id),
                'expected': str(shift.expected_cash),
                'actual': str(shift.actual_cash),
                'difference': str(shift.cash_difference),
            }
        )


class CashDrop(models.Model):
    """
    Cash Drop / Setoran Kasir - Track cash removal from register to safe
    For security and reconciliation purposes
    """
    REASON_CHOICES = [
        ('regular', 'Regular Drop'),
        ('excess', 'Excess Cash'),
        ('safe_deposit', 'Safe Deposit'),
        ('bank_deposit', 'Bank Deposit Prep'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Multi-tenant fields (complete hierarchy)
    company = models.ForeignKey('Company', on_delete=models.PROTECT, related_name='cash_drops')
    brand = models.ForeignKey('Brand', on_delete=models.PROTECT, related_name='cash_drops')
    store = models.ForeignKey('Store', on_delete=models.PROTECT, related_name='cash_drops')
    
    # Shift relationship
    cashier_shift = models.ForeignKey(CashierShift, on_delete=models.PROTECT, related_name='cash_drops')
    
    # Transaction details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='regular')
    notes = models.TextField(blank=True)
    
    # User tracking
    created_by = models.ForeignKey('User', on_delete=models.PROTECT, related_name='cash_drops_created')
    approved_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='cash_drops_approved')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    
    # Receipt tracking
    receipt_number = models.CharField(max_length=50, unique=True)
    receipt_printed = models.BooleanField(default=False)
    printed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'core_cash_drop'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'brand', 'store']),
            models.Index(fields=['cashier_shift', 'created_at']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['receipt_number']),
        ]
    
    def __str__(self):
        return f"Cash Drop {self.receipt_number} - Rp {self.amount:,.0f}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Generate receipt number: CD-STORECODE-YYYYMMDD-XXX
            from django.db.models import Max
            today = timezone.now().date()
            store_code = self.store.store_code if self.store else 'UNKN'
            prefix = f"CD-{store_code}-{today.strftime('%Y%m%d')}"
            
            last_drop = CashDrop.objects.filter(
                receipt_number__startswith=prefix,
                store=self.store
            ).aggregate(Max('receipt_number'))
            
            if last_drop['receipt_number__max']:
                last_num = int(last_drop['receipt_number__max'].split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.receipt_number = f"{prefix}-{new_num:03d}"
        
        super().save(*args, **kwargs)
    
    def mark_printed(self):
        """Mark receipt as printed"""
        self.receipt_printed = True
        self.printed_at = timezone.now()
        self.save(update_fields=['receipt_printed', 'printed_at'])

