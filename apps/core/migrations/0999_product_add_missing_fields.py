# Generated manually
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_initial'),
    ]

    operations = [
        # Add sort_order field
        migrations.AddField(
            model_name='product',
            name='sort_order',
            field=models.IntegerField(default=0, help_text='Display order for product listing'),
        ),
        
        # Add company_id field
        migrations.AddField(
            model_name='product',
            name='company',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='core.company',
                help_text='Company that owns this product'
            ),
        ),
        
        # Change stock_quantity from integer to decimal to match HO
        migrations.AlterField(
            model_name='product',
            name='stock_quantity',
            field=models.DecimalField(
                default=0,
                max_digits=10,
                decimal_places=2,
                help_text='Current stock quantity'
            ),
        ),
    ]
