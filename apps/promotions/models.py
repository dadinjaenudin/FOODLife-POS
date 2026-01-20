from django.db import models
from django.utils import timezone
from decimal import Decimal


class Promotion(models.Model):
    TYPE_CHOICES = [
        ('percent_discount', 'Percent Discount'),
        ('amount_discount', 'Amount Discount'),
        ('buy_x_get_y', 'Buy X Get Y'),
        ('combo', 'Combo Price'),
        ('free_item', 'Free Item'),
    ]
    
    APPLY_TO_CHOICES = [
        ('all', 'All Products'),
        ('category', 'Specific Category'),
        ('product', 'Specific Product'),
        ('bill', 'Entire Bill'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    promo_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    apply_to = models.CharField(max_length=20, choices=APPLY_TO_CHOICES, default='all')
    
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    buy_quantity = models.IntegerField(default=0)
    get_quantity = models.IntegerField(default=0)
    get_product = models.ForeignKey(
        'core.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='free_promos'
    )
    
    combo_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    combo_products = models.ManyToManyField('core.Product', blank=True, related_name='combo_promos')
    
    categories = models.ManyToManyField('core.Category', blank=True)
    products = models.ManyToManyField('core.Product', blank=True, related_name='promos')
    outlet = models.ForeignKey('core.Outlet', on_delete=models.CASCADE, related_name='promotions')
    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    valid_days = models.JSONField(default=list, blank=True)
    valid_time_start = models.TimeField(null=True, blank=True)
    valid_time_end = models.TimeField(null=True, blank=True)
    
    max_uses = models.IntegerField(default=0)
    max_uses_per_customer = models.IntegerField(default=0)
    current_uses = models.IntegerField(default=0)
    
    min_purchase = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    min_quantity = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    is_auto_apply = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def is_valid_now(self):
        now = timezone.now()
        
        if not (self.start_date <= now <= self.end_date):
            return False
        
        if self.valid_days and now.weekday() not in self.valid_days:
            return False
        
        if self.valid_time_start and self.valid_time_end:
            current_time = now.time()
            if not (self.valid_time_start <= current_time <= self.valid_time_end):
                return False
        
        if self.max_uses > 0 and self.current_uses >= self.max_uses:
            return False
        
        return self.is_active
    
    def calculate_discount(self, bill):
        if not self.is_valid_now():
            return Decimal('0')
        
        if bill.subtotal < self.min_purchase:
            return Decimal('0')
        
        discount = Decimal('0')
        
        if self.promo_type == 'percent_discount':
            if self.apply_to == 'bill':
                discount = bill.subtotal * (self.discount_percent / 100)
            elif self.apply_to == 'category':
                applicable_total = sum(
                    item.total for item in bill.items.filter(
                        product__category__in=self.categories.all(),
                        is_void=False
                    )
                )
                discount = applicable_total * (self.discount_percent / 100)
            elif self.apply_to == 'product':
                applicable_total = sum(
                    item.total for item in bill.items.filter(
                        product__in=self.products.all(),
                        is_void=False
                    )
                )
                discount = applicable_total * (self.discount_percent / 100)
        
        elif self.promo_type == 'amount_discount':
            discount = self.discount_amount
        
        elif self.promo_type == 'buy_x_get_y':
            qualifying_items = bill.items.filter(
                product__in=self.products.all(),
                is_void=False
            )
            total_qty = sum(item.quantity for item in qualifying_items)
            free_count = (total_qty // self.buy_quantity) * self.get_quantity
            
            if self.get_product:
                discount = self.get_product.price * free_count
            else:
                prices = sorted([item.unit_price for item in qualifying_items])
                discount = sum(prices[:free_count])
        
        return min(discount, bill.subtotal)


class Voucher(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('used', 'Used'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='vouchers')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_name = models.CharField(max_length=200, blank=True)
    
    qr_code = models.ImageField(upload_to='vouchers/', blank=True)
    
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True)
    used_bill = models.ForeignKey('pos.Bill', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.code
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        super().save(*args, **kwargs)
    
    def generate_code(self):
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    def generate_qr_code(self):
        import qrcode
        from io import BytesIO
        from django.core.files import File
        
        qr = qrcode.make(self.code)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        self.qr_code.save(f'voucher_{self.code}.png', File(buffer), save=True)
    
    def is_valid(self):
        if self.status != 'active':
            return False, f"Voucher {self.status}"
        
        if self.expires_at and timezone.now() > self.expires_at:
            self.status = 'expired'
            self.save()
            return False, "Voucher expired"
        
        if not self.promotion.is_valid_now():
            return False, "Promo tidak berlaku"
        
        return True, "Valid"
    
    def redeem(self, bill, user):
        is_valid, message = self.is_valid()
        if not is_valid:
            return False, message
        
        self.status = 'used'
        self.used_at = timezone.now()
        self.used_by = user
        self.used_bill = bill
        self.save()
        
        self.promotion.current_uses += 1
        self.promotion.save()
        
        return True, "Voucher berhasil digunakan"


class BillPromotion(models.Model):
    bill = models.ForeignKey('pos.Bill', on_delete=models.CASCADE, related_name='applied_promos')
    promotion = models.ForeignKey(Promotion, on_delete=models.PROTECT)
    voucher = models.ForeignKey(Voucher, on_delete=models.SET_NULL, null=True, blank=True)
    
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2)
    applied_at = models.DateTimeField(auto_now_add=True)
    applied_by = models.ForeignKey('core.User', on_delete=models.PROTECT)
    
    def __str__(self):
        return f"{self.bill.bill_number} - {self.promotion.name}"
