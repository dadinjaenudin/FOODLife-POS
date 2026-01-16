from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


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
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    tax_id = models.CharField(max_length=50, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=11.00)
    service_charge = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    logo = models.ImageField(upload_to='outlets/', blank=True)
    receipt_footer = models.TextField(blank=True, default='Terima Kasih Atas Kunjungan Anda')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


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
    sku = models.CharField(max_length=50, unique=True)
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
