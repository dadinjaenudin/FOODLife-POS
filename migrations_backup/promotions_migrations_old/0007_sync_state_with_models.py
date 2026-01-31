# Generated manually to sync migration state with current models
# This migration does nothing because the database schema is already correct
# from migration 0005 (rebuild) and 0006 (drop unused tables)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('promotions', '0006_drop_unused_tables'),
    ]

    operations = [
        # No operations needed - database schema already matches models
        # Models:
        #   - Promotion (table: promotions_promotion) - UUID PK, denormalized with JSON fields
        #   - PromotionUsage (table: promotion_usage) - usage tracking
        #   - PromotionSyncLog (table: promotion_sync_log) - sync logging
        #
        # All old models removed:
        #   - PackagePromotion, PromotionTier, Voucher, BillPromotion, etc.
        #   - All ManyToMany relationship tables dropped
    ]
