import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_payment_profiles'),
    ]

    operations = [
        migrations.CreateModel(
            name='EFTTerminal',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(help_text='EFT terminal code (e.g. 01, 02)', max_length=10)),
                ('name', models.CharField(help_text='Bank/terminal name (e.g. BCA, MANDIRI)', max_length=100)),
                ('sort_order', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='eft_terminals', to='core.company')),
            ],
            options={
                'db_table': 'core_eft_terminal',
                'ordering': ['sort_order', 'code'],
                'unique_together': {('company', 'code')},
            },
        ),
    ]
