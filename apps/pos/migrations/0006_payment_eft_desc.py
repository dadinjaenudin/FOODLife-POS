from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0005_payment_method_flex'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='eft_desc',
            field=models.CharField(blank=True, help_text='Denormalized EFT terminal description, e.g. "01: BCA"', max_length=120),
        ),
    ]
