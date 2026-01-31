# Generated manually to sync Modifier and ModifierOption state with database
# Database schema is already correct from migration 0009 (raw SQL CREATE TABLE)
# This migration only updates Django's migration state

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_alter_product_unique_together'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # No database operations - schema already correct from migration 0009
            ],
            state_operations=[
                # Update migration state to reflect that Modifier and ModifierOption exist
                migrations.CreateModel(
                    name='Modifier',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('name', models.CharField(max_length=200)),
                        ('is_required', models.BooleanField(default=False)),
                        ('max_selections', models.IntegerField(default=1)),
                        ('is_active', models.BooleanField(default=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modifiers', to='core.brand')),
                    ],
                    options={
                        'db_table': 'core_modifier',
                        'ordering': ['name'],
                    },
                ),
                
                migrations.CreateModel(
                    name='ModifierOption',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('name', models.CharField(max_length=200)),
                        ('price_adjustment', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                        ('is_default', models.BooleanField(default=False)),
                        ('sort_order', models.IntegerField(default=0)),
                        ('is_active', models.BooleanField(default=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('modifier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='core.modifier')),
                    ],
                    options={
                        'db_table': 'core_modifier_option',
                        'ordering': ['sort_order', 'name'],
                    },
                ),
            ],
        ),
    ]
