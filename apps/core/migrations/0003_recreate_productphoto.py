# Generated manually to recreate ProductPhoto table

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductPhoto',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('object_key', models.CharField(blank=True, help_text='Path di Edge MinIO', max_length=500)),
                ('filename', models.CharField(blank=True, max_length=255)),
                ('size', models.IntegerField(blank=True, help_text='File size in bytes', null=True)),
                ('content_type', models.CharField(blank=True, default='image/jpeg', max_length=100)),
                ('checksum', models.CharField(blank=True, help_text='MD5 or SHA256 checksum', max_length=64)),
                ('version', models.IntegerField(default=1, help_text='Version for cache busting')),
                ('is_primary', models.BooleanField(default=False, help_text='Primary/main product image')),
                ('sort_order', models.IntegerField(default=0, help_text='Display order')),
                ('caption', models.CharField(blank=True, max_length=200)),
                ('is_active', models.BooleanField(default=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='products/gallery/')),
                ('last_sync_at', models.DateTimeField(blank=True, help_text='Last synced from HO', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='core.product')),
            ],
            options={
                'db_table': 'core_productphoto',
                'ordering': ['sort_order', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='productphoto',
            index=models.Index(fields=['product', 'is_primary'], name='core_produc_product_a76660_idx'),
        ),
        migrations.AddIndex(
            model_name='productphoto',
            index=models.Index(fields=['product', 'sort_order'], name='core_produc_product_a117ef_idx'),
        ),
    ]
