# Generated manually to fix migration state
# This migration brings the migration history in sync with current models
# Database schema is already correct from migration 0005 (rebuild) and 0006 (drop tables)

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('promotions', '0007_sync_state_with_models'),
        ('core', '0010_add_product_modifier_model'),
    ]

    # This replaces the promotion model definition in migration state to match current models.py
    # No actual database operations needed as schema was rebuilt in migration 0005
    
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                # Remove all old model definitions that no longer exist
                migrations.DeleteModel(name='BillPromotion'),
                migrations.DeleteModel(name='CustomerPromotionHistory'),
                migrations.DeleteModel(name='PackageItem'),
                migrations.DeleteModel(name='PackagePromotion'),
                migrations.DeleteModel(name='PromotionApproval'),
                migrations.DeleteModel(name='PromotionLog'),
                migrations.DeleteModel(name='PromotionTier'),
                migrations.DeleteModel(name='Voucher'),
                
                # Remove the old Promotion model with all its M2M fields
                migrations.RemoveField(model_name='promotion', name='brands'),
                migrations.RemoveField(model_name='promotion', name='cannot_combine_with'),
                migrations.RemoveField(model_name='promotion', name='categories'),
                migrations.RemoveField(model_name='promotion', name='combo_products'),
                migrations.RemoveField(model_name='promotion', name='company'),
                migrations.RemoveField(model_name='promotion', name='created_by'),
                migrations.RemoveField(model_name='promotion', name='exclude_brands'),
                migrations.RemoveField(model_name='promotion', name='exclude_categories'),
                migrations.RemoveField(model_name='promotion', name='exclude_members'),
                migrations.RemoveField(model_name='promotion', name='exclude_products'),
                migrations.RemoveField(model_name='promotion', name='get_product'),
                migrations.RemoveField(model_name='promotion', name='products'),
                migrations.RemoveField(model_name='promotion', name='required_product'),
                migrations.RemoveField(model_name='promotion', name='upsell_product'),
                migrations.RemoveField(model_name='promotion', name='brand'),
                
                migrations.DeleteModel(name='Promotion'),
                migrations.DeleteModel(name='PromotionUsage'),
                
                # Recreate models with new denormalized schema (matching models.py)
                migrations.CreateModel(
                    name='Promotion',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('code', models.CharField(db_index=True, max_length=50, unique=True)),
                        ('name', models.CharField(max_length=255)),
                        ('description', models.TextField(blank=True, default='')),
                        ('terms_conditions', models.TextField(blank=True, default='')),
                        ('promo_type', models.CharField(max_length=50)),
                        ('apply_to', models.CharField(max_length=20)),
                        ('execution_stage', models.CharField(max_length=20)),
                        ('execution_priority', models.IntegerField(default=500)),
                        ('is_active', models.BooleanField(default=True)),
                        ('is_auto_apply', models.BooleanField(default=False)),
                        ('require_voucher', models.BooleanField(default=False)),
                        ('member_only', models.BooleanField(default=False)),
                        ('is_stackable', models.BooleanField(default=False)),
                        ('start_date', models.DateField()),
                        ('end_date', models.DateField()),
                        ('time_start', models.TimeField(blank=True, null=True)),
                        ('time_end', models.TimeField(blank=True, null=True)),
                        ('valid_days', models.TextField(blank=True, default='')),
                        ('exclude_holidays', models.BooleanField(default=False)),
                        ('rules_json', models.TextField()),
                        ('scope_json', models.TextField(blank=True, default='')),
                        ('targeting_json', models.TextField(blank=True, default='')),
                        ('max_uses', models.IntegerField(blank=True, null=True)),
                        ('max_uses_per_customer', models.IntegerField(blank=True, null=True)),
                        ('max_uses_per_day', models.IntegerField(blank=True, null=True)),
                        ('current_uses', models.IntegerField(default=0)),
                        ('compiled_at', models.DateTimeField()),
                        ('synced_at', models.DateTimeField(auto_now=True)),
                        ('last_used_at', models.DateTimeField(blank=True, null=True)),
                        ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='promotions', to='core.company')),
                        ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='promotions', to='core.brand')),
                        ('store', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='promotions', to='core.store')),
                    ],
                    options={
                        'db_table': 'promotions_promotion',
                        'ordering': ['-start_date', 'execution_priority', 'name'],
                    },
                ),
                
                migrations.CreateModel(
                    name='PromotionUsage',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('promotion_code', models.CharField(max_length=50)),
                        ('transaction_id', models.UUIDField()),
                        ('order_number', models.CharField(blank=True, max_length=50)),
                        ('customer_id', models.UUIDField(blank=True, null=True)),
                        ('customer_phone', models.CharField(blank=True, max_length=20)),
                        ('member_tier', models.CharField(blank=True, max_length=50)),
                        ('discount_amount', models.DecimalField(decimal_places=2, max_digits=15)),
                        ('original_amount', models.DecimalField(decimal_places=2, max_digits=15)),
                        ('final_amount', models.DecimalField(decimal_places=2, max_digits=15)),
                        ('used_at', models.DateTimeField(auto_now_add=True)),
                        ('usage_date', models.DateField()),
                        ('promotion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usages', to='promotions.promotion')),
                        ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.brand')),
                        ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.store')),
                    ],
                    options={
                        'db_table': 'promotion_usage',
                    },
                ),
            ],
            database_operations=[
                # No database operations - schema already correct
            ],
        ),
    ]

