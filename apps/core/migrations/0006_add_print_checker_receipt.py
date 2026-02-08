# Generated migration for print_checker_receipt field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_add_posterminal_print_to'),
    ]

    operations = [
        migrations.AddField(
            model_name='posterminal',
            name='print_checker_receipt',
            field=models.BooleanField(
                default=False,
                help_text='Print checker receipt when sending to kitchen (for marking completed items)'
            ),
        ),
    ]
