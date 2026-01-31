"""
Promotion Models - Denormalized schema for fast querying
Based on Edge Server design principles
"""
from django.db import models
import uuid
import json


class Promotion(models.Model):
    """
    Main promotions table - denormalized for fast querying
    Stores all promotion data synced from CMS
    """
    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Info
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    terms_conditions = models.TextField(blank=True, default='')
    
    # Multi-tenant Context
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='promotions')
    brand = models.ForeignKey('core.Brand', on_delete=models.CASCADE, related_name='promotions')
    store = models.ForeignKey('core.Store', on_delete=models.CASCADE, related_name='promotions', null=True, blank=True)
    
    # Type & Configuration
    promo_type = models.CharField(max_length=50)  # percent_discount, buy_x_get_y, etc.
    apply_to = models.CharField(max_length=20)  # all, category, product
    execution_stage = models.CharField(max_length=20)  # item_level, cart_level, payment_level
    execution_priority = models.IntegerField(default=500)
    
    # Flags
    is_active = models.BooleanField(default=True)
    is_auto_apply = models.BooleanField(default=False)
    require_voucher = models.BooleanField(default=False)
    member_only = models.BooleanField(default=False)
    is_stackable = models.BooleanField(default=False)
    
    # Validity (Denormalized for fast filtering)
    start_date = models.DateField()
    end_date = models.DateField()
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    valid_days = models.TextField(blank=True, default='')  # JSON array
    exclude_holidays = models.BooleanField(default=False)
    
    # Rules (JSON - Full promotion rules)
    rules_json = models.TextField()  # JSON string
    
    # Scope (JSON - Product/Category targeting)
    scope_json = models.TextField(blank=True, default='')  # JSON string
    
    # Targeting (JSON - Store/Brand/Customer targeting)
    targeting_json = models.TextField(blank=True, default='')  # JSON string
    
    # Limits
    max_uses = models.IntegerField(null=True, blank=True)
    max_uses_per_customer = models.IntegerField(null=True, blank=True)
    max_uses_per_day = models.IntegerField(null=True, blank=True)
    current_uses = models.IntegerField(default=0)
    
    # Metadata
    compiled_at = models.DateTimeField()
    synced_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'promotions_promotion'
        ordering = ['-start_date', 'execution_priority', 'name']
        indexes = [
            models.Index(fields=['company', 'store']),
            models.Index(fields=['brand']),
            models.Index(fields=['is_active', 'start_date', 'end_date']),
            models.Index(fields=['promo_type']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_rules(self):
        """Parse and return rules JSON as dict"""
        import json
        if self.rules_json:
            try:
                if isinstance(self.rules_json, str):
                    return json.loads(self.rules_json)
                return self.rules_json
            except:
                return {}
        return {}
    
    def get_scope(self):
        """Parse and return scope JSON as dict"""
        import json
        if self.scope_json:
            try:
                if isinstance(self.scope_json, str):
                    return json.loads(self.scope_json)
                return self.scope_json
            except:
                return {}
        return {}
    
    def get_targeting(self):
        """Parse and return targeting JSON as dict"""
        import json
        if self.targeting_json:
            try:
                if isinstance(self.targeting_json, str):
                    return json.loads(self.targeting_json)
                return self.targeting_json
            except:
                return {}
        return {}
    
    def is_valid_now(self):
        """Check if promotion is currently valid"""
        from django.utils import timezone
        now = timezone.now()
        today = now.date()
        current_time = now.time()
        
        # Check date range
        if not (self.start_date <= today <= self.end_date):
            return False
        
        # Check time range if specified
        if self.time_start and self.time_end:
            if not (self.time_start <= current_time <= self.time_end):
                return False
        
        # Check active status
        if not self.is_active:
            return False
        
        return True
    
    def get_rules(self):
        """Parse rules JSON"""
        try:
            return json.loads(self.rules_json) if self.rules_json else {}
        except:
            return {}
    
    def get_scope(self):
        """Parse scope JSON"""
        try:
            return json.loads(self.scope_json) if self.scope_json else {}
        except:
            return {}
    
    def get_targeting(self):
        """Parse targeting JSON"""
        try:
            return json.loads(self.targeting_json) if self.targeting_json else {}
        except:
            return {}
    
    def get_valid_days(self):
        """Parse valid days JSON"""
        try:
            return json.loads(self.valid_days) if self.valid_days else []
        except:
            return []
    
    def get_discount_amount(self, original_amount):
        """Calculate discount amount based on rules"""
        rules = self.get_rules()
        
        if rules.get('type') == 'percent':
            discount_percent = rules.get('discount_percent', 0)
            discount = original_amount * (discount_percent / 100)
            
            # Apply max discount if specified
            max_discount = rules.get('max_discount_amount')
            if max_discount and discount > max_discount:
                discount = max_discount
            
            return discount
        
        elif rules.get('type') == 'fixed':
            return rules.get('discount_amount', 0)
        
        return 0
    
    def can_apply_to_product(self, product_id):
        """Check if promotion applies to specific product"""
        scope = self.get_scope()
        apply_to = scope.get('apply_to', 'all')
        
        if apply_to == 'all':
            # Check if product is excluded
            excluded = scope.get('exclude_products', [])
            return str(product_id) not in excluded
        
        # Add more logic for specific products/categories
        return False


class PromotionUsage(models.Model):
    """Track promotion usage for limits enforcement"""
    
    # References
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='usages')
    promotion_code = models.CharField(max_length=50)
    
    # Transaction Info
    transaction_id = models.UUIDField()
    order_number = models.CharField(max_length=50, blank=True)
    
    # Customer Info
    customer_id = models.UUIDField(null=True, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    member_tier = models.CharField(max_length=50, blank=True)
    
    # Usage Details
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2)
    original_amount = models.DecimalField(max_digits=15, decimal_places=2)
    final_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Context
    brand = models.ForeignKey('core.Brand', on_delete=models.CASCADE)
    store = models.ForeignKey('core.Store', on_delete=models.CASCADE)
    
    # Timestamp
    used_at = models.DateTimeField(auto_now_add=True)
    usage_date = models.DateField()
    
    class Meta:
        db_table = 'promotion_usage'
        indexes = [
            models.Index(fields=['promotion', 'usage_date']),
            models.Index(fields=['promotion', 'customer_id', 'usage_date']),
            models.Index(fields=['transaction_id']),
        ]
    
    def __str__(self):
        return f"{self.promotion_code} - {self.usage_date}"


class PromotionSyncLog(models.Model):
    """Track sync operations for debugging and monitoring"""
    
    SYNC_TYPE_CHOICES = [
        ('full', 'Full Sync'),
        ('incremental', 'Incremental'),
        ('manual', 'Manual'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ]
    
    # Sync Info
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPE_CHOICES)
    sync_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Statistics
    promotions_received = models.IntegerField(default=0)
    promotions_added = models.IntegerField(default=0)
    promotions_updated = models.IntegerField(default=0)
    promotions_deleted = models.IntegerField(default=0)
    
    # Context
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE)
    store = models.ForeignKey('core.Store', on_delete=models.CASCADE)
    
    # Error Info
    error_message = models.TextField(blank=True)
    error_details = models.TextField(blank=True)
    
    # Timestamp
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    
    # Metadata
    cms_version = models.CharField(max_length=20, blank=True)
    edge_version = models.CharField(max_length=20, blank=True)
    
    class Meta:
        db_table = 'promotion_sync_log'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['started_at']),
            models.Index(fields=['sync_status']),
        ]
    
    def __str__(self):
        return f"{self.sync_type} - {self.sync_status} - {self.started_at}"
