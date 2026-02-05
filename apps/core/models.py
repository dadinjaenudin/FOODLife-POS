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
    last_sync = models.DateTimeField(null=True, blank=True)
    
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
        if ip_address:
            self.ip_address = ip_address
        self.save(update_fields=['last_heartbeat', 'ip_address'])
    
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

