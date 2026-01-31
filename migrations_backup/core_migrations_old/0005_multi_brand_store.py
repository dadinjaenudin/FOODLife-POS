# Generated manually for multi-brand store architecture
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_add_loyalty_config'),
    ]

    operations = [
        # Step 1: Add company field as nullable first
        migrations.AddField(
            model_name='store',
            name='company',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='stores',
                to='core.company'
            ),
        ),
        
        # Step 2: Populate company from brand (for existing data)
        migrations.RunSQL(
            """
            UPDATE core_store 
            SET company_id = (
                SELECT company_id FROM core_brand WHERE core_brand.id = core_store.brand_id
            )
            WHERE brand_id IS NOT NULL;
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
        
        # Step 3: Make company non-nullable
        migrations.AlterField(
            model_name='store',
            name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='stores',
                to='core.company'
            ),
        ),
        
        # Step 4: Create StoreBrand model
        migrations.CreateModel(
            name='StoreBrand',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('ho_store_id', models.UUIDField(blank=True, help_text='HO Store ID that represents this brand in this physical store', null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='brand_stores', to='core.brand')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='store_brands', to='core.store')),
            ],
            options={
                'verbose_name': 'Store Brand',
                'verbose_name_plural': 'Store Brands',
                'db_table': 'core_storebrand',
                'ordering': ['brand__name'],
            },
        ),
        
        # Step 5: Add unique constraint
        migrations.AddConstraint(
            model_name='storebrand',
            constraint=models.UniqueConstraint(fields=['store', 'brand'], name='unique_store_brand'),
        ),
        
        # Step 6: Migrate existing Store.brand to StoreBrand
        migrations.RunSQL(
            """
            INSERT INTO core_storebrand (id, store_id, brand_id, is_active, created_at, updated_at)
            SELECT 
                gen_random_uuid(),
                id,
                brand_id,
                true,
                now(),
                now()
            FROM core_store
            WHERE brand_id IS NOT NULL;
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
        
        # Step 7: Add brand to POSTerminal
        migrations.AddField(
            model_name='posterminal',
            name='brand',
            field=models.ForeignKey(
                blank=True,
                help_text='Brand this terminal serves (required for multi-brand stores)',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='terminals',
                to='core.brand'
            ),
        ),
        
        # Step 8: Populate terminal.brand from store.brand (for existing terminals)
        migrations.RunSQL(
            """
            UPDATE core_posterminal 
            SET brand_id = (
                SELECT brand_id FROM core_store WHERE core_store.id = core_posterminal.store_id
            )
            WHERE store_id IS NOT NULL;
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
        
        # Step 9: Remove old brand FK from Store
        migrations.RemoveField(
            model_name='store',
            name='brand',
        ),
    ]
