"""
Add company/store FK to PaymentMethodProfile, make brand nullable.
Populate company from existing brand FK before making it non-nullable.
"""
import django.db.models.deletion
from django.db import migrations, models


def populate_company_from_brand(apps, schema_editor):
    """Set company from brand for all existing PaymentMethodProfile rows"""
    PaymentMethodProfile = apps.get_model('core', 'PaymentMethodProfile')
    for profile in PaymentMethodProfile.objects.select_related('brand').all():
        if profile.brand_id:
            profile.company_id = profile.brand.company_id
            profile.save(update_fields=['company_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_customer_review'),
    ]

    operations = [
        # Step 1: Add company as nullable
        migrations.AddField(
            model_name='paymentmethodprofile',
            name='company',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='payment_profiles',
                to='core.company',
            ),
        ),

        # Step 2: Add store as nullable
        migrations.AddField(
            model_name='paymentmethodprofile',
            name='store',
            field=models.ForeignKey(
                blank=True,
                help_text='Leave empty for brand-wide or company-wide profile',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='payment_profiles',
                to='core.store',
            ),
        ),

        # Step 3: Populate company from brand
        migrations.RunPython(populate_company_from_brand, migrations.RunPython.noop),

        # Step 4: Make company non-nullable
        migrations.AlterField(
            model_name='paymentmethodprofile',
            name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='payment_profiles',
                to='core.company',
            ),
        ),

        # Step 5: Make brand nullable
        migrations.AlterField(
            model_name='paymentmethodprofile',
            name='brand',
            field=models.ForeignKey(
                blank=True,
                help_text='Leave empty for company-wide profile',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='payment_profiles',
                to='core.brand',
            ),
        ),

        # Step 6: Remove old unique_together and index, add new index
        migrations.AlterUniqueTogether(
            name='paymentmethodprofile',
            unique_together=set(),
        ),
        migrations.RemoveIndex(
            model_name='paymentmethodprofile',
            name='core_paymen_brand_i_879553_idx',
        ),
        migrations.AddIndex(
            model_name='paymentmethodprofile',
            index=models.Index(fields=['company', 'is_active'], name='core_paymen_company_6b1c2e_idx'),
        ),
    ]
