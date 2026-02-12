from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid


class Company(models.Model):
    """Top-level tenant for multi-tenant system"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='companies/', blank=True)
    timezone = models.CharField(max_length=50, default='Asia/Jakarta')
    is_active = models.BooleanField(default=True)
    
    # Loyalty Program Configuration
    point_expiry_months = models.IntegerField(
        default=12,
        help_text="Points expire after X months (0 = never expire)"
    )
    points_per_currency = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        help_text="Points earned per currency unit (e.g., 1.00 = 1 point per Rp 1)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Companies'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('cashier', 'Kasir'),
        ('waiter', 'Waiter'),
        ('kitchen', 'Kitchen Staff'),
    ]
    
    ROLE_SCOPE_CHOICES = [
        ('store', 'Store Level'),      # Manager shift - hanya 1 store
        ('brand', 'Brand Level'),       # Area manager - semua store dalam 1 brand
        ('company', 'Company Level'),   # HO admin - semua brand & store
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier')
    role_scope = models.CharField(
        max_length=20, 
        choices=ROLE_SCOPE_CHOICES, 
        default='store',
        help_text="Scope of authority: store manager vs area manager vs HO admin"
    )
    pin = models.CharField(max_length=6, blank=True)
    brand = models.ForeignKey('Brand', on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey('Company', on_delete=models.SET_NULL, null=True, blank=True)
    profile_photo = models.ImageField(upload_to='users/profiles/', blank=True, null=True)
    
    def has_permission(self, permission):
        """Check role-based permission"""
        permissions = {
            'admin': ['all'],
            'manager': ['void_item', 'cancel_bill', 'discount', 'reports', 'reprint'],
            'cashier': ['create_bill', 'payment', 'reprint'],
            'waiter': ['create_bill', 'modify_order'],
            'kitchen': ['view_orders', 'update_status'],
        }
        user_perms = permissions.get(self.role, [])
        return 'all' in user_perms or permission in user_perms
    
    def can_approve_for_brand(self, brand):
        """Check if user can approve transactions for a specific brand"""
        # Company-level scope can approve for any brand
        if self.role_scope == 'company':
            return True
        
        # Brand-level scope can approve only for their assigned brand
        if self.role_scope == 'brand':
            return self.brand_id == brand.id if brand else False
        
        # Store-level scope cannot approve cross-store (handled by can_approve_for_store)
        return False
    
    def can_approve_for_store(self, store):
        """Check if user can approve transactions for a specific store"""
        from apps.core.models import Store
        
        # Company-level scope can approve for any store
        if self.role_scope == 'company':
            return True
        
        # Brand-level scope can approve for any store in their brand
        if self.role_scope == 'brand' and store:
            return self.brand_id == store.brand_id
        
        # Store-level scope can only approve for their current store
        # (Determined by terminal/session context in view)
        return False


class Brand(models.Model):
    """Brand/Concept within a company (e.g., 'Ayam Geprek', 'Bakso Boedjangan')"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='brands')
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    tax_id = models.CharField(max_length=50, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=11.00)
    service_charge = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    logo = models.ImageField(upload_to='brands/', blank=True)
    receipt_footer = models.TextField(blank=True, default='Terima Kasih Atas Kunjungan Anda')
    brand_type = models.CharField(
        max_length=50,
        default='restaurant',
        help_text='Type of brand/concept (synced from HO)'
    )
    is_active = models.BooleanField(default=True)
    
    # Brand-specific loyalty override (optional)
    point_expiry_months_override = models.IntegerField(
        null=True,
        blank=True,
        help_text="Override company point expiry policy for this brand (null = use company default)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_point_expiry_months(self):
        """Get effective point expiry months (brand override or company default)"""
        return self.point_expiry_months_override if self.point_expiry_months_override is not None else self.company.point_expiry_months
    
    class Meta:
        db_table = 'core_brand'
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
        unique_together = [['company', 'code']]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.company.name} - {self.name}"


class Store(models.Model):
    """Physical store location - Singleton per Edge Server, can have multiple brands"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='stores')
    store_code = models.CharField(max_length=20, unique=True)
    store_name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    timezone = models.CharField(max_length=50, default='Asia/Jakarta')
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    login_image = models.ImageField(upload_to='login_images/', blank=True, null=True, help_text='Image for login page (recommended 1080x1920)')
    is_active = models.BooleanField(default=True)
    configured_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_store'
        verbose_name = 'Store'
        verbose_name_plural = 'Stores'
    
    def __str__(self):
        return f"{self.store_name} ({self.store_code})"
    
    def save(self, *args, **kwargs):
        # Enforce singleton pattern
        if not self.pk and Store.objects.exists():
            raise ValueError('Store configuration already exists. Only one store per Edge Server.')
        return super().save(*args, **kwargs)
    
    @classmethod
    def get_current(cls):
        """Get current store configuration"""
        return cls.objects.first()
    
    def get_primary_brand(self):
        """Get the primary/first active brand for this store (for backward compatibility)"""
        store_brand = self.store_brands.filter(is_active=True).first()
        return store_brand.brand if store_brand else None
    
    def get_all_brands(self):
        """Get all active brands for this store"""
        return [sb.brand for sb in self.store_brands.filter(is_active=True)]
    
    @property
    def brand(self):
        """Backward compatibility property - returns primary brand"""
        return self.get_primary_brand()


class StoreBrand(models.Model):
    """Many-to-Many: Store can have multiple Brands (Food Court concept)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='store_brands')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='brand_stores')
    
    # Reference to HO Store for this brand (for sync)
    ho_store_id = models.UUIDField(
        null=True, 
        blank=True,
        help_text="HO Store ID that represents this brand in this physical store"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_storebrand'
        unique_together = [['store', 'brand']]
        ordering = ['brand__name']
        verbose_name = 'Store Brand'
        verbose_name_plural = 'Store Brands'
    
    def __str__(self):
        return f"{self.store.store_name} - {self.brand.name}"


class POSTerminal(models.Model):
    """POS/Tablet/Kiosk device registration - assigned to specific brand"""
    DEVICE_TYPE_CHOICES = [
        ('pos', 'POS / Kasir'),
        ('tablet', 'Tablet / Waiter'),
        ('kiosk', 'Self-Service Kiosk'),
        ('kitchen_display', 'Kitchen Display'),
    ]
    
    PRINTER_TYPE_CHOICES = [
        ('thermal', 'Thermal Printer (58mm/80mm)'),
        ('dot_matrix', 'Dot Matrix'),
        ('laser', 'Laser Printer'),
        ('none', 'No Printer'),
    ]
    
    EDC_MODE_CHOICES = [
        ('none', 'No EDC Integration'),
        ('manual', 'Manual Entry'),
        ('api', 'API Integration'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='terminals', null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='terminals', null=True, blank=True,
                              help_text="Brand this terminal serves (required for multi-brand stores)")
    terminal_code = models.CharField(max_length=20, unique=True)
    terminal_name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPE_CHOICES)
    
    # Network information
    mac_address = models.CharField(max_length=17, blank=True, help_text='MAC Address (auto-detected)')
    ip_address = models.GenericIPAddressField(blank=True, null=True, help_text='Last known IP address')
    user_agent = models.TextField(blank=True, help_text='Browser user agent')
    
    # Status tracking
    is_active = models.BooleanField(default=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True, help_text='Last ping timestamp')
    last_seen = models.DateTimeField(null=True, blank=True, help_text='Last activity timestamp')
    last_sync = models.DateTimeField(null=True, blank=True)
    
    # Session management for launcher authentication
    session_token = models.UUIDField(null=True, blank=True, help_text='Launcher session token')
    token_expires_at = models.DateTimeField(null=True, blank=True, help_text='Session token expiry')
    
    # Printer Configuration
    printer_type = models.CharField(max_length=20, choices=PRINTER_TYPE_CHOICES, default='thermal')
    receipt_printer_name = models.CharField(max_length=200, blank=True, help_text='Receipt printer name/path')
    receipt_paper_width = models.IntegerField(default=80, help_text='Paper width in mm (58 or 80)')
    kitchen_printer_name = models.CharField(max_length=200, blank=True, help_text='Kitchen printer name/path')
    print_logo_on_receipt = models.BooleanField(default=True)
    auto_print_receipt = models.BooleanField(default=False, help_text='Auto print after payment')
    auto_print_kitchen_order = models.BooleanField(default=True, help_text='Auto print kitchen tickets')
    
    PRINT_TO_CHOICES = [
        ('printer', 'Printer'),
        ('file', 'File'),
    ]
    print_to = models.CharField(
        max_length=20,
        choices=PRINT_TO_CHOICES,
        default='printer',
        help_text='Print destination: printer or file (for development)'
    )
    print_checker_receipt = models.BooleanField(
        default=False,
        help_text='Print checker receipt when sending to kitchen (for marking completed items)'
    )
    
    # Hardware Integration
    cash_drawer_enabled = models.BooleanField(default=False)
    barcode_scanner_enabled = models.BooleanField(default=False)
    customer_pole_display_enabled = models.BooleanField(default=False)
    
    # Display Configuration
    enable_customer_display = models.BooleanField(default=False, help_text='Enable dual display for customer')
    enable_kitchen_display = models.BooleanField(default=False, help_text='Enable kitchen display screen')
    enable_kitchen_printer = models.BooleanField(default=True, help_text='Enable kitchen printer')
    
    # Payment Configuration
    default_payment_methods = models.JSONField(
        default=list,
        blank=True,
        help_text='Default payment methods enabled for this terminal (e.g., ["cash", "qris", "card"])'
    )
    edc_integration_mode = models.CharField(
        max_length=20,
        choices=EDC_MODE_CHOICES,
        default='none',
        help_text='EDC/Card payment integration mode'
    )
    payment_profiles = models.ManyToManyField(
        'PaymentMethodProfile',
        blank=True,
        related_name='terminals',
        help_text='Payment method profiles assigned to this terminal'
    )

    registered_at = models.DateTimeField(auto_now_add=True)
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['terminal_code']
        indexes = [
            models.Index(fields=['terminal_code']),
            models.Index(fields=['is_active', 'last_heartbeat']),
        ]
    
    def __str__(self):
        return f"{self.terminal_code} - {self.terminal_name}"
    
    def update_heartbeat(self, ip_address=None):
        """Update last heartbeat and optionally IP address"""
        self.last_heartbeat = timezone.now()
        self.last_seen = timezone.now()
        if ip_address:
            self.ip_address = ip_address
        self.save(update_fields=['last_heartbeat', 'last_seen', 'ip_address'])
    
    def generate_session_token(self, expiry_hours=24):
        """Generate new session token for launcher authentication"""
        import uuid
        self.session_token = uuid.uuid4()
        self.token_expires_at = timezone.now() + timezone.timedelta(hours=expiry_hours)
        self.save(update_fields=['session_token', 'token_expires_at'])
        return self.session_token
    
    def validate_session_token(self, token):
        """Validate session token and check expiry"""
        if not self.session_token or not self.token_expires_at:
            return False
        if str(self.session_token) != str(token):
            return False
        if timezone.now() > self.token_expires_at:
            return False
        return True
    
    @property
    def is_online(self):
        """Check if terminal is online (heartbeat within 5 minutes)"""
        if not self.last_heartbeat:
            return False
        threshold = timezone.now() - timezone.timedelta(minutes=5)
        return self.last_heartbeat > threshold


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='categories')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    icon = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name


class Product(models.Model):
    PRINTER_CHOICES = [
        ('kitchen', 'Kitchen Printer'),
        ('bar', 'Bar Printer'),
        ('dessert', 'Dessert Station'),
        ('none', 'No Print'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products', null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, help_text='Company that owns this product')
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    image = models.ImageField(upload_to='products/', blank=True)
    description = models.TextField(blank=True)
    
    printer_target = models.CharField(max_length=20, choices=PRINTER_CHOICES, default='kitchen')
    
    is_active = models.BooleanField(default=True)
    track_stock = models.BooleanField(default=False)
    stock_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Current stock quantity')
    low_stock_alert = models.IntegerField(default=10)
    sort_order = models.IntegerField(default=0, help_text='Display order for product listing')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'name']
        unique_together = [['brand', 'category', 'name', 'sku']]
        indexes = [
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['brand', 'category']),
        ]
    
    def __str__(self):
        return self.name


class Modifier(models.Model):
    """Modifier groups for products (e.g., Size, Spice Level)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='modifiers')
    is_required = models.BooleanField(default=False)
    max_selections = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_modifier'
        indexes = [
            models.Index(fields=['brand', 'is_active']),
        ]
    
    def __str__(self):
        return self.name


class ProductModifier(models.Model):
    """Through model for Product-Modifier relationship with sort order"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_modifiers')
    modifier = models.ForeignKey(Modifier, on_delete=models.CASCADE, related_name='product_modifiers')
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'core_product_modifier'
        unique_together = [['product', 'modifier']]
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['modifier']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.modifier.name}"


# Add property to Product to access modifiers
def get_modifiers(self):
    """Get all modifiers for this product"""
    return Modifier.objects.filter(product_modifiers__product=self)

Product.add_to_class('get_modifiers', property(lambda self: get_modifiers(self)))



class ModifierOption(models.Model):
    """Individual modifier options"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    modifier = models.ForeignKey(Modifier, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=200)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_default = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_modifier_option'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['modifier', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.modifier.name} - {self.name}"


class ProductPhoto(models.Model):
    """Additional product photos for gallery - synced with HO MinIO"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='photos')
    
    # MinIO storage fields
    object_key = models.CharField(max_length=500, blank=True, help_text='Path di Edge MinIO')
    filename = models.CharField(max_length=255, blank=True)
    size = models.IntegerField(null=True, blank=True, help_text='File size in bytes')
    content_type = models.CharField(max_length=100, blank=True, default='image/jpeg')
    checksum = models.CharField(max_length=64, blank=True, help_text='MD5 or SHA256 checksum')
    version = models.IntegerField(default=1, help_text='Version for cache busting')
    
    # Display settings
    is_primary = models.BooleanField(default=False, help_text='Primary/main product image')
    sort_order = models.IntegerField(default=0, help_text='Display order')
    caption = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Legacy field (deprecated - use object_key)
    image = models.ImageField(upload_to='products/gallery/', blank=True, null=True)
    
    # Sync tracking
    last_sync_at = models.DateTimeField(null=True, blank=True, help_text='Last synced from HO')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_productphoto'
        ordering = ['sort_order', '-created_at']
        indexes = [
            models.Index(fields=['product', 'is_primary']),
            models.Index(fields=['product', 'sort_order']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - Photo {self.filename or self.id}"
    
    def get_url(self):
        """Get URL for photo - prioritize MinIO object_key"""
        if self.object_key:
            # Return MinIO URL (will be implemented in settings)
            from django.conf import settings
            minio_url = getattr(settings, 'MINIO_EXTERNAL_URL', 'http://localhost:9002')
            bucket = getattr(settings, 'MINIO_BUCKET', 'product-images')
            return f"{minio_url}/{bucket}/{self.object_key}"
        elif self.image:
            return self.image.url
        return None


class Member(models.Model):
    """Customer loyalty/membership program"""
    TIER_CHOICES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='members')
    
    # Member Identity
    member_code = models.CharField(max_length=20, unique=True, db_index=True)
    card_number = models.CharField(max_length=50, blank=True, help_text='Physical card number')
    
    # Personal Info
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, db_index=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    
    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    
    # Membership Info
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='bronze')
    joined_date = models.DateField(auto_now_add=True)
    expire_date = models.DateField(null=True, blank=True)
    
    # Points & Balance
    points = models.IntegerField(default=0)
    point_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Statistics
    total_visits = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    last_visit = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='members_created')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'member_code']),
            models.Index(fields=['company', 'phone']),
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['tier', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.member_code} - {self.full_name}"
    
    def save(self, *args, **kwargs):
        if not self.member_code:
            self.member_code = self.generate_member_code()
        super().save(*args, **kwargs)
    
    def generate_member_code(self):
        """Generate member code: MB-COMPANYCODE-YYYYMM-XXXX"""
        from django.db.models import Max
        today = timezone.now()
        company_code = self.company.code if self.company else 'XX'
        prefix = f"MB-{company_code}-{today.strftime('%Y%m')}"
        
        last_member = Member.objects.filter(
            member_code__startswith=prefix,
            company=self.company
        ).aggregate(Max('member_code'))
        
        if last_member['member_code__max']:
            last_num = int(last_member['member_code__max'].split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}-{new_num:04d}"
    
    def add_points(self, amount):
        """Add points based on purchase amount (e.g., 1 point per 10000)"""
        points_earned = int(amount / 10000)
        self.points += points_earned
        self.save(update_fields=['points'])
        return points_earned
    
    def update_statistics(self, bill_amount):
        """Update member statistics after purchase"""
        self.total_visits += 1
        self.total_spent += bill_amount
        self.last_visit = timezone.now()
        self.save(update_fields=['total_visits', 'total_spent', 'last_visit'])


class MemberTransaction(models.Model):
    """Track member points and balance transactions"""
    TRANSACTION_TYPE_CHOICES = [
        ('earn', 'Earn Points'),
        ('redeem', 'Redeem Points'),
        ('topup', 'Top Up Balance'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
        ('expired', 'Points Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='transactions')
    bill = models.ForeignKey('pos.Bill', on_delete=models.SET_NULL, null=True, blank=True, related_name='member_transactions')
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    points_change = models.IntegerField(default=0, help_text='Positive for earn, negative for redeem')
    balance_change = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    points_before = models.IntegerField(default=0)
    points_after = models.IntegerField(default=0)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['member', 'created_at']),
            models.Index(fields=['transaction_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.member.member_code} - {self.transaction_type} - {self.created_at.date()}"


class CustomerDisplaySlide(models.Model):
    """
    Slideshow images for customer display
    Images stored in MinIO, metadata in database
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='customer_slides')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='customer_slides', null=True, blank=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='customer_slides', null=True, blank=True)
    
    title = models.CharField(max_length=200, help_text="Slide title (for admin only)")
    description = models.TextField(blank=True, help_text="Description (for admin only)")
    
    # MinIO storage
    image_url = models.URLField(max_length=500, help_text="Full MinIO URL to image")
    image_path = models.CharField(max_length=500, help_text="MinIO object path (bucket/key)")
    
    # Display settings
    order = models.IntegerField(default=0, help_text="Display order (lower = first)")
    duration_seconds = models.IntegerField(default=5, help_text="How long to show this slide")
    
    # Status and scheduling
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True, help_text="Start showing from this date (optional)")
    end_date = models.DateField(null=True, blank=True, help_text="Stop showing after this date (optional)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='slides_created')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='slides_updated')
    
    class Meta:
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['company', 'is_active', 'order']),
            models.Index(fields=['brand', 'is_active', 'order']),
            models.Index(fields=['store', 'is_active', 'order']),
        ]
        verbose_name = 'Customer Display Slide'
        verbose_name_plural = 'Customer Display Slides'
    
    def __str__(self):
        scope = "All"
        if self.store:
            scope = f"Store: {self.store.code}"
        elif self.brand:
            scope = f"Brand: {self.brand.code}"
        return f"{self.title} ({scope}) - Order: {self.order}"
    
    def is_valid_for_date(self, check_date=None):
        """Check if slide should be shown on given date"""
        if check_date is None:
            check_date = timezone.now().date()
        
        if self.start_date and check_date < self.start_date:
            return False
        if self.end_date and check_date > self.end_date:
            return False
        return True


class CustomerDisplayConfig(models.Model):
    """
    Configuration for customer display appearance
    Controls branding, theme colors, and running text
    One config per company/brand/store combination
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='display_configs')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='display_configs', null=True, blank=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='display_configs', null=True, blank=True)
    
    # Branding
    brand_name = models.CharField(max_length=200, help_text="Display name on customer screen")
    brand_logo = models.ImageField(upload_to='display_logos/', null=True, blank=True, help_text="Upload brand logo")
    brand_logo_url = models.URLField(max_length=500, blank=True, help_text="Logo URL (MinIO) - optional if logo uploaded")
    brand_tagline = models.CharField(max_length=200, blank=True, help_text="Tagline below brand name")
    
    # Running Text
    running_text = models.TextField(help_text="Scrolling text at bottom of screen")
    running_text_speed = models.IntegerField(default=50, help_text="Scroll speed (pixels per second)")
    
    # Theme Colors
    theme_primary_color = models.CharField(max_length=20, default='#4F46E5', help_text="Primary color (hex)")
    theme_secondary_color = models.CharField(max_length=20, default='#10B981', help_text="Secondary color (hex)")
    theme_text_color = models.CharField(max_length=20, default='#1F2937', help_text="Main text color (hex)")
    theme_billing_bg = models.CharField(max_length=50, default='gradient', help_text="Billing section background")
    theme_billing_text = models.CharField(max_length=20, default='#FFFFFF', help_text="Billing text color (hex)")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='display_configs_created')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='display_configs_updated')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['store', 'is_active']),
        ]
        unique_together = [['company', 'brand', 'store']]
        verbose_name = 'Customer Display Config'
        verbose_name_plural = 'Customer Display Configs'
    
    def __str__(self):
        scope = "All"
        if self.store:
            scope = f"Store: {self.store.code}"
        elif self.brand:
            scope = f"Brand: {self.brand.code}"
        return f"{self.brand_name} ({scope})"
    
    def get_logo_url(self, request=None):
        """
        Get logo URL - prioritize uploaded file over brand_logo_url
        Returns absolute URL if request provided, relative URL otherwise
        """
        if self.brand_logo:
            if request:
                return request.build_absolute_uri(self.brand_logo.url)
            return self.brand_logo.url
        return self.brand_logo_url or ''


def receipt_logo_upload_path(instance, filename):
    """
    Generate dynamic upload path for receipt template logo
    Path: receipt_logos/{company_code}/{brand_code or 'company'}/{timestamp}_{filename}
    """
    import os
    from datetime import datetime
    
    # Get company code
    company_code = instance.company.code if instance.company else 'default'
    
    # Get brand code or use 'company' for company-wide templates
    if instance.brand:
        scope_code = instance.brand.code
    elif instance.store:
        scope_code = f"store_{instance.store.code}"
    else:
        scope_code = 'company'
    
    # Add timestamp to filename to avoid collisions
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(filename)
    new_filename = f"{timestamp}_{name}{ext}"
    
    # Return path: receipt_logos/{company_code}/{scope_code}/{timestamp}_{filename}
    return os.path.join('receipt_logos', company_code, scope_code, new_filename)


class ReceiptTemplate(models.Model):
    """
    Receipt printing template configuration
    Controls receipt header, content display, and footer
    """
    PRICE_ALIGNMENT_CHOICES = [
        ('left', 'Left'),
        ('right', 'Right'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='receipt_templates')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='receipt_templates', null=True, blank=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='receipt_templates', null=True, blank=True)
    
    # Template Info
    template_name = models.CharField(max_length=100, help_text="Template identifier")
    is_active = models.BooleanField(default=True)
    
    # Paper Settings
    paper_width = models.IntegerField(default=58, help_text="Paper width in mm (58 or 80)")
    
    # Header
    show_logo = models.BooleanField(default=True)
    logo = models.ImageField(upload_to=receipt_logo_upload_path, null=True, blank=True, help_text="Receipt logo image")
    header_line_1 = models.CharField(max_length=100, blank=True, help_text="Store name / company")
    header_line_2 = models.CharField(max_length=100, blank=True, help_text="Address line 1")
    header_line_3 = models.CharField(max_length=100, blank=True, help_text="Address line 2 / Phone")
    header_line_4 = models.CharField(max_length=100, blank=True, help_text="Tax ID / Additional info")
    
    # Content Display Options
    show_receipt_number = models.BooleanField(default=True)
    show_date_time = models.BooleanField(default=True)
    show_cashier_name = models.BooleanField(default=True)
    show_customer_name = models.BooleanField(default=True)
    show_table_number = models.BooleanField(default=True)
    show_item_code = models.BooleanField(default=False)
    show_item_category = models.BooleanField(default=False)
    show_modifiers = models.BooleanField(default=True)
    
    # Formatting
    price_alignment = models.CharField(max_length=10, choices=PRICE_ALIGNMENT_CHOICES, default='right')
    show_currency_symbol = models.BooleanField(default=True)
    
    # Summary Section
    show_subtotal = models.BooleanField(default=True)
    show_tax = models.BooleanField(default=True)
    show_service_charge = models.BooleanField(default=True)
    show_discount = models.BooleanField(default=True)
    show_payment_method = models.BooleanField(default=True)
    show_paid_amount = models.BooleanField(default=True)
    show_change = models.BooleanField(default=True)
    
    # Footer
    footer_line_1 = models.CharField(max_length=100, blank=True, help_text="Thank you message")
    footer_line_2 = models.CharField(max_length=100, blank=True, help_text="Additional info")
    footer_line_3 = models.CharField(max_length=100, blank=True, help_text="Website / Social media")
    show_qr_payment = models.BooleanField(default=False, help_text="Show payment QR code")
    
    # Print Settings
    auto_print = models.BooleanField(default=True, help_text="Auto print after order")
    auto_cut = models.BooleanField(default=True, help_text="Auto cut paper")
    feed_lines = models.IntegerField(default=3, help_text="Lines to feed after print")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='receipt_templates_created')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='receipt_templates_updated')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['store', 'is_active']),
        ]
        verbose_name = 'Receipt Template'
        verbose_name_plural = 'Receipt Templates'
    
    def __str__(self):
        scope = "Company"
        if self.store:
            scope = f"{self.store.name}"
        elif self.brand:
            scope = f"{self.brand.name}"
        return f"{self.template_name} ({scope})"
    
    def save(self, *args, **kwargs):
        """Override save to delete old logo when uploading new one"""
        try:
            # Get old instance to check if logo changed
            if self.pk:
                old_instance = ReceiptTemplate.objects.get(pk=self.pk)
                # If logo changed, delete old file
                if old_instance.logo and old_instance.logo != self.logo:
                    import os
                    if os.path.isfile(old_instance.logo.path):
                        os.remove(old_instance.logo.path)
        except ReceiptTemplate.DoesNotExist:
            pass
        except Exception as e:
            # Don't fail save if cleanup fails
            print(f"[Warning] Failed to cleanup old logo: {e}")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Override delete to cleanup logo file"""
        try:
            # Delete logo file before deleting instance
            if self.logo:
                import os
                if os.path.isfile(self.logo.path):
                    os.remove(self.logo.path)
        except Exception as e:
            # Don't fail delete if cleanup fails
            print(f"[Warning] Failed to cleanup logo on delete: {e}")
        
        super().delete(*args, **kwargs)


class MediaGroup(models.Model):
    """Payment media grouping for reporting and Orafin integration"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='media_groups')

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    orafin_group = models.CharField(max_length=100, blank=True, help_text='Orafin mapping group for financial integration')

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_media_group'
        unique_together = [['company', 'code']]
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class PaymentMethodProfile(models.Model):
    """Configurable payment method profile with dynamic data entry prompts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey('Brand', on_delete=models.CASCADE, related_name='payment_profiles')
    media_group = models.ForeignKey(MediaGroup, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payment_profiles')

    media_id = models.IntegerField(default=0, help_text='Media ID from backoffice keyboard mapping')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    color = models.CharField(max_length=20, default='#6b7280', help_text='Button color hex')
    icon = models.CharField(max_length=50, blank=True, help_text='Icon identifier')
    sort_order = models.IntegerField(default=0)

    smallest_denomination = models.IntegerField(default=0,
        help_text='Smallest denomination allowed (0 = any amount)')
    allow_change = models.BooleanField(default=False,
        help_text='Whether overpayment returns change (True for cash)')
    open_cash_drawer = models.BooleanField(default=False,
        help_text='Whether to trigger cash drawer on this payment method')

    legacy_method_id = models.CharField(max_length=20, blank=True,
        help_text='Maps to old method IDs: cash, card, qris, ewallet, transfer, voucher, debit')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_payment_method_profile'
        unique_together = [['brand', 'code']]
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['brand', 'is_active']),
        ]

    def __str__(self):
        return f"{self.brand.name} - {self.name}"


class DataEntryPrompt(models.Model):
    """Data entry field definition for a payment method profile"""
    FIELD_TYPE_CHOICES = [
        ('amount', 'Amount'),
        ('text', 'Text Input'),
        ('numeric', 'Numeric Input'),
        ('scanner', 'Scanner Input'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(PaymentMethodProfile, on_delete=models.CASCADE, related_name='prompts')

    field_name = models.CharField(max_length=50)
    label = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default='text')

    min_length = models.IntegerField(default=0, help_text='Minimum input length (0 = optional)')
    max_length = models.IntegerField(default=99, help_text='Maximum input length')

    placeholder = models.CharField(max_length=200, blank=True)
    use_scanner = models.BooleanField(default=False, help_text='Enable barcode/QR scanner for this field')
    is_required = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_data_entry_prompt'
        ordering = ['sort_order']
        unique_together = [['profile', 'field_name']]

    def __str__(self):
        return f"{self.profile.name} - {self.label}"


class EFTTerminal(models.Model):
    """Master data for EFT (Electronic Funds Transfer) terminal/bank codes.
    Used as reference lookup when cashier inputs EFT terminal number during card payments."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='eft_terminals')

    code = models.CharField(max_length=10, help_text='EFT terminal code (e.g. 01, 02)')
    name = models.CharField(max_length=100, help_text='Bank/terminal name (e.g. BCA, MANDIRI)')

    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_eft_terminal'
        unique_together = [['company', 'code']]
        ordering = ['sort_order', 'code']

    def __str__(self):
        return f"{self.code}: {self.name}"

