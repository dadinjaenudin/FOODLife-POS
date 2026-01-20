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
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier')
    pin = models.CharField(max_length=6, blank=True)
    outlet = models.ForeignKey('Outlet', on_delete=models.SET_NULL, null=True, blank=True)
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


class Outlet(models.Model):
    """Brand/Concept within a company"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='outlets')
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    tax_id = models.CharField(max_length=50, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=11.00)
    service_charge = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    logo = models.ImageField(upload_to='outlets/', blank=True)
    receipt_footer = models.TextField(blank=True, default='Terima Kasih Atas Kunjungan Anda')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['company', 'code']]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.company.name} - {self.name}"


class StoreConfig(models.Model):
    """Singleton configuration for Edge Server - identifies which store this server represents"""
    outlet = models.ForeignKey(Outlet, on_delete=models.PROTECT)
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
        verbose_name = 'Store Configuration'
        verbose_name_plural = 'Store Configuration'
    
    def __str__(self):
        return f"{self.outlet.name} - {self.store_name}"
    
    def save(self, *args, **kwargs):
        # Enforce singleton pattern
        if not self.pk and StoreConfig.objects.exists():
            raise ValueError('Store configuration already exists. Only one store per Edge Server.')
        return super().save(*args, **kwargs)
    
    @classmethod
    def get_current(cls):
        """Get current store configuration"""
        return cls.objects.first()


class POSTerminal(models.Model):
    """POS/Tablet/Kiosk device registration"""
    DEVICE_TYPE_CHOICES = [
        ('pos', 'POS / Kasir'),
        ('tablet', 'Tablet / Waiter'),
        ('kiosk', 'Self-Service Kiosk'),
        ('kitchen_display', 'Kitchen Display'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(StoreConfig, on_delete=models.CASCADE, related_name='terminals', null=True, blank=True)
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
    name = models.CharField(max_length=100)
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE, related_name='categories')
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
    
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, db_index=True)  # Removed unique=True to allow duplicate SKU
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    image = models.ImageField(upload_to='products/', blank=True)
    description = models.TextField(blank=True)
    
    printer_target = models.CharField(max_length=20, choices=PRINTER_CHOICES, default='kitchen')
    
    is_active = models.BooleanField(default=True)
    track_stock = models.BooleanField(default=False)
    stock_quantity = models.IntegerField(default=0)
    low_stock_alert = models.IntegerField(default=10)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Modifier(models.Model):
    """Modifier groups for products (e.g., Size, Spice Level)"""
    name = models.CharField(max_length=100)
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, related_name='modifiers', blank=True)
    is_required = models.BooleanField(default=False)
    max_selections = models.IntegerField(default=1)
    
    def __str__(self):
        return self.name


class ModifierOption(models.Model):
    """Individual modifier options"""
    modifier = models.ForeignKey(Modifier, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=100)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_default = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.modifier.name} - {self.name}"


class ProductPhoto(models.Model):
    """Additional product photos for gallery"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='products/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', '-uploaded_at']
    
    def __str__(self):
        return f"{self.product.name} - Photo {self.id}"

