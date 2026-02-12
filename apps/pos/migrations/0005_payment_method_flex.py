from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0004_payment_profile_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='method',
            field=models.CharField(max_length=50),
        ),
    ]
