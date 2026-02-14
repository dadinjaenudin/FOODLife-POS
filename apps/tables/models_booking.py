from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid


class ReservationConfig(models.Model):
    """Konfigurasi Booking per Store — OneToOne"""
    DEPOSIT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.OneToOneField('core.Store', on_delete=models.CASCADE, related_name='reservation_config')

    is_booking_enabled = models.BooleanField(default=False, help_text='Aktifkan/nonaktifkan fitur booking')
    default_slot_duration = models.IntegerField(default=120, help_text='Durasi default per slot (menit)')
    max_advance_days = models.IntegerField(default=30, help_text='Maks booking berapa hari ke depan')
    grace_period_minutes = models.IntegerField(default=30, help_text='Toleransi keterlambatan sebelum no-show')

    require_deposit = models.BooleanField(default=False, help_text='Default apakah deposit wajib')
    default_deposit_type = models.CharField(max_length=20, choices=DEPOSIT_TYPE_CHOICES, default='percentage')
    default_deposit_value = models.DecimalField(max_digits=12, decimal_places=2, default=50, help_text='Nilai deposit (50 = 50% atau Rp 50.000)')
    min_deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=50000, help_text='Minimum deposit amount')

    cancellation_hours = models.IntegerField(default=24, help_text='Batas jam pembatalan tanpa penalty')
    cancellation_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Persentase penalty pembatalan')
    auto_noshow_minutes = models.IntegerField(default=0, help_text='0 = manual no-show only')
    overbooking_buffer = models.IntegerField(default=30, help_text='Buffer menit antar booking di meja yang sama')
    max_party_size = models.IntegerField(default=50, help_text='Max tamu per booking')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tables_reservation_config'

    def __str__(self):
        return f"Booking Config - {self.store}"


class ReservationPackage(models.Model):
    """Paket Event/Private Dining"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='reservation_packages', null=True, blank=True)
    brand = models.ForeignKey('core.Brand', on_delete=models.CASCADE, related_name='reservation_packages')

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    min_pax = models.IntegerField(default=1)
    max_pax = models.IntegerField(default=50)
    price_per_pax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fixed_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='Harga flat (alternatif per-pax)')
    includes_menu = models.BooleanField(default=False)
    menu_items = models.JSONField(default=list, blank=True, help_text='Daftar menu yang termasuk')
    duration_hours = models.IntegerField(default=3)
    deposit_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=50, help_text='Override deposit % untuk paket ini')
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tables_reservation_package'
        ordering = ['name']
        indexes = [
            models.Index(fields=['brand', 'is_active']),
        ]

    def __str__(self):
        return self.name

    def get_price_for_pax(self, pax_count):
        """Calculate total price for given pax count"""
        if self.fixed_price > 0:
            return self.fixed_price
        return self.price_per_pax * pax_count


class Reservation(models.Model):
    """Data Booking Utama"""
    TYPE_CHOICES = [
        ('standard', 'Standard'),
        ('min_spend', 'Minimum Spend'),
        ('event', 'Event / Private Dining'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('deposit_pending', 'Deposit Pending'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    DEPOSIT_STATUS_CHOICES = [
        ('none', 'No Deposit'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('refunded', 'Refunded'),
        ('forfeited', 'Forfeited'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation_code = models.CharField(max_length=20, unique=True, blank=True)

    # Multi-tenant
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='reservations', null=True, blank=True)
    brand = models.ForeignKey('core.Brand', on_delete=models.CASCADE, related_name='reservations')
    store = models.ForeignKey('core.Store', on_delete=models.CASCADE, related_name='reservations', null=True, blank=True)

    # Type & Status
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='standard')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Schedule
    reservation_date = models.DateField()
    time_start = models.TimeField()
    time_end = models.TimeField()
    duration_minutes = models.IntegerField(default=120)

    # Guest
    guest_name = models.CharField(max_length=100)
    guest_phone = models.CharField(max_length=20, blank=True, default='')
    guest_email = models.CharField(max_length=100, blank=True, default='')
    party_size = models.IntegerField(default=2)

    # Tables (M2M)
    tables = models.ManyToManyField('tables.Table', blank=True, related_name='reservations')
    table_area = models.ForeignKey('tables.TableArea', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations')

    # Financial
    minimum_spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deposit_required = models.BooleanField(default=False)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deposit_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deposit_status = models.CharField(max_length=20, choices=DEPOSIT_STATUS_CHOICES, default='none')

    # Event
    package = models.ForeignKey(ReservationPackage, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations')
    special_requests = models.TextField(blank=True, default='')

    # Relations
    bill = models.ForeignKey('pos.Bill', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations')
    member = models.ForeignKey('core.Member', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations')
    created_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, related_name='reservations_created')
    confirmed_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_confirmed')

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, default='')
    noshow_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tables_reservation'
        ordering = ['reservation_date', 'time_start']
        indexes = [
            models.Index(fields=['brand', 'store', 'reservation_date']),
            models.Index(fields=['status', 'reservation_date']),
            models.Index(fields=['reservation_code']),
            models.Index(fields=['guest_phone']),
        ]

    def __str__(self):
        return f"{self.reservation_code} - {self.guest_name} ({self.reservation_date})"

    def save(self, *args, **kwargs):
        if not self.reservation_code:
            self.reservation_code = self.generate_code()
        super().save(*args, **kwargs)

    def generate_code(self):
        date_str = self.reservation_date.strftime('%Y%m%d') if self.reservation_date else timezone.now().strftime('%Y%m%d')
        prefix = f"RSV-{date_str}"
        last = Reservation.objects.filter(reservation_code__startswith=prefix).order_by('-reservation_code').first()
        if last:
            try:
                last_num = int(last.reservation_code.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        return f"{prefix}-{new_num:03d}"

    @property
    def is_past_grace_period(self):
        """Check if reservation is past grace period"""
        if self.status != 'confirmed':
            return False
        now = timezone.localtime()
        reservation_datetime = timezone.make_aware(
            timezone.datetime.combine(self.reservation_date, self.time_start)
        )
        config = getattr(self.store, 'reservation_config', None)
        grace = config.grace_period_minutes if config else 30
        return now > reservation_datetime + timezone.timedelta(minutes=grace)

    @property
    def time_until_reservation(self):
        """Human-readable time until reservation"""
        now = timezone.localtime()
        reservation_datetime = timezone.make_aware(
            timezone.datetime.combine(self.reservation_date, self.time_start)
        )
        delta = reservation_datetime - now
        if delta.total_seconds() < 0:
            minutes_late = abs(delta.total_seconds()) // 60
            return f"{int(minutes_late)} menit terlambat"
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        if delta.days > 0:
            return f"{delta.days} hari lagi"
        if hours > 0:
            return f"{hours} jam {minutes} menit lagi"
        return f"{minutes} menit lagi"

    def can_cancel(self):
        """Check if reservation can be cancelled"""
        return self.status in ('pending', 'deposit_pending', 'confirmed')

    def get_refund_amount(self):
        """Calculate refund amount based on cancellation policy"""
        if self.deposit_paid <= 0:
            return Decimal('0')

        config = getattr(self.store, 'reservation_config', None)
        if not config:
            return self.deposit_paid

        now = timezone.localtime()
        reservation_datetime = timezone.make_aware(
            timezone.datetime.combine(self.reservation_date, self.time_start)
        )
        hours_before = (reservation_datetime - now).total_seconds() / 3600

        if hours_before > config.cancellation_hours:
            return self.deposit_paid  # Full refund
        else:
            fee = self.deposit_paid * (config.cancellation_fee_pct / 100)
            return self.deposit_paid - fee


class ReservationDeposit(models.Model):
    """Tracking Pembayaran Deposit"""
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
        ('forfeited', 'Forfeited'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='deposits')

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    payment_profile = models.ForeignKey(
        'core.PaymentMethodProfile', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reservation_deposits'
    )
    payment_metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='paid')

    paid_at = models.DateTimeField(auto_now_add=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_reason = models.TextField(blank=True, default='')
    receipt_number = models.CharField(max_length=50, blank=True, default='')

    created_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, related_name='reservation_deposits_created')

    class Meta:
        db_table = 'tables_reservation_deposit'
        ordering = ['-paid_at']
        indexes = [
            models.Index(fields=['reservation', 'status']),
        ]

    def __str__(self):
        return f"Deposit {self.reservation.reservation_code} - Rp {self.amount}"


class ReservationLog(models.Model):
    """Audit Trail untuk Reservation"""
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('confirmed', 'Confirmed'),
        ('deposit_paid', 'Deposit Paid'),
        ('checked_in', 'Checked In'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('modified', 'Modified'),
    ]

    id = models.BigAutoField(primary_key=True)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tables_reservation_log'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.action}] {self.reservation.reservation_code}"
