from django.db import models


class TableArea(models.Model):
    """Area/Zone dalam restoran"""
    name = models.CharField(max_length=100)
    outlet = models.ForeignKey('core.Outlet', on_delete=models.CASCADE, related_name='areas')
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class TableGroup(models.Model):
    """Group of joined tables"""
    main_table = models.ForeignKey('Table', on_delete=models.CASCADE, related_name='led_groups')
    outlet = models.ForeignKey('core.Outlet', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True)
    
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
    
    number = models.CharField(max_length=20)
    area = models.ForeignKey(TableArea, on_delete=models.CASCADE, related_name='tables')
    capacity = models.IntegerField(default=4)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True)
    
    table_group = models.ForeignKey(
        TableGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tables'
    )
    
    pos_x = models.IntegerField(default=0)
    pos_y = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['number', 'area']
        ordering = ['area', 'number']
    
    def __str__(self):
        return f"{self.area.name} - {self.number}"
    
    def get_active_bill(self):
        return self.bills.filter(status__in=['open', 'hold']).first()
    
    def generate_qr_code(self):
        """Generate QR code for table ordering"""
        import qrcode
        from django.conf import settings
        from io import BytesIO
        from django.core.files import File
        
        url = f"{settings.BASE_URL}/order/{self.area.outlet.id}/{self.id}/"
        qr = qrcode.make(url)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        self.qr_code.save(f'table_{self.id}.png', File(buffer), save=True)
