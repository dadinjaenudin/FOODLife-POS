# Generated migration for logo field in ReceiptTemplate

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_posterminal_auto_print_kitchen_order_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='receipttemplate',
            name='logo',
            field=models.ImageField(blank=True, help_text='Receipt logo image', null=True, upload_to='receipt_logos/'),
        ),
    ]
