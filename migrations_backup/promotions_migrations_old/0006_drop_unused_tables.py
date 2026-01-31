# Generated manually for edge server cleanup
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('promotions', '0005_rebuild_promotions_denormalized'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Drop ManyToMany relationship tables (not used in denormalized schema)
            DROP TABLE IF EXISTS promotions_promotion_brands CASCADE;
            DROP TABLE IF EXISTS promotions_promotion_cannot_combine_with CASCADE;
            DROP TABLE IF EXISTS promotions_promotion_categories CASCADE;
            DROP TABLE IF EXISTS promotions_promotion_combo_products CASCADE;
            DROP TABLE IF EXISTS promotions_promotion_exclude_brands CASCADE;
            DROP TABLE IF EXISTS promotions_promotion_exclude_categories CASCADE;
            DROP TABLE IF EXISTS promotions_promotion_exclude_members CASCADE;
            DROP TABLE IF EXISTS promotions_promotion_exclude_products CASCADE;
            DROP TABLE IF EXISTS promotions_promotion_products CASCADE;
            
            -- Drop old approval/log models (not used in edge server)
            DROP TABLE IF EXISTS promotions_promotionapproval CASCADE;
            DROP TABLE IF EXISTS promotions_promotionlog CASCADE;
            
            -- Drop extended models (package, tier, voucher, etc - not used in edge)
            DROP TABLE IF EXISTS promotions_packagepromotion CASCADE;
            DROP TABLE IF EXISTS promotions_packageitem CASCADE;
            DROP TABLE IF EXISTS promotions_promotiontier CASCADE;
            DROP TABLE IF EXISTS promotions_voucher CASCADE;
            DROP TABLE IF EXISTS promotions_billpromotion CASCADE;
            DROP TABLE IF EXISTS promotions_customerpromotionhistory CASCADE;
            
            -- Drop old promotionusage table (with 's' prefix and bigint PK)
            -- NOTE: promotion_usage (without 's', with UUID) is kept and still used
            DROP TABLE IF EXISTS promotions_promotionusage CASCADE;
            """,
            reverse_sql="""
            -- Cannot reverse - tables will be dropped
            -- If needed, restore from backup or rerun initial migrations
            """
        ),
    ]
