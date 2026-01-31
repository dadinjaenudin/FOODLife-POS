from django.db import models
import uuid


class TableArea(models.Model):
    """Area/Zone dalam restoran"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    brand = models.ForeignKey('core.Brand', on_delete=models.CASCADE, related_name='areas')
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='table_areas', null=True, blank=True)
    store = models.ForeignKey('core.Store', on_delete=models.CASCADE, related_name='table_areas', null=True, blank=True)
    description = models.TextField(blank=True, default='')
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Floor plan fields
    floor_width = models.IntegerField(null=True, blank=True)
    floor_height = models.IntegerField(null=True, blank=True)
    floor_image = models.ImageField(upload_to='floor_plans/', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tables_tablearea'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['store', 'is_active']),
        ]
    
    def __str__(self):
        return self.name


class TableGroup(models.Model):
    """Group of joined tables"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    main_table = models.ForeignKey('Table', on_delete=models.CASCADE, related_name='led_groups')
    brand = models.ForeignKey('core.Brand', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'tables_tablegroup'
        indexes = [
            models.Index(fields=['brand', 'created_at']),
            models.Index(fields=['main_table']),
        ]
    
    def get_all_tables(self):
        return Table.objects.filter(table_group=self)
    
    def get_total_capacity(self):
        return sum(t.capacity for t in self.get_all_tables())


class Table(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('billing', 'Billing'),
        ('dirty', 'Needs Cleaning'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(max_length=20)
    area = models.ForeignKey(TableArea, on_delete=models.CASCADE, related_name='tables')
    capacity = models.IntegerField(default=4)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    qr_code = models.CharField(max_length=200, blank=True)  # Changed from ImageField to CharField to match HO
    is_active = models.BooleanField(default=True)
    
    table_group = models.ForeignKey(
        TableGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tables'
    )
    
    pos_x = models.IntegerField(null=True, blank=True)
    pos_y = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tables_table'
        ordering = ['area', 'number']
        indexes = [
            models.Index(fields=['area', 'is_active']),
            models.Index(fields=['number']),
        ]
    
    def __str__(self):
        return f"{self.area.name} - {self.number}"
    
    def get_active_bill(self):
        return self.bills.filter(status__in=['open', 'hold']).first()
    
    def generate_qr_code(self):
        """Generate QR code URL for table ordering"""
        from django.conf import settings
        # Store QR code URL instead of image
        self.qr_code = f"{settings.BASE_URL}/order/{self.area.brand.id}/{self.id}/"
        self.save(update_fields=['qr_code'])
