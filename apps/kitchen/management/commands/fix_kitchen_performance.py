from django.core.management.base import BaseCommand
from django.db import connection
from decimal import Decimal, InvalidOperation


class Command(BaseCommand):
    help = 'Fix invalid decimal values in KitchenPerformance table'

    def handle(self, *args, **options):
        self.stdout.write('Fixing invalid decimal values in KitchenPerformance...')
        
        # Direct SQL to fix invalid decimal values
        with connection.cursor() as cursor:
            # First, check all values
            cursor.execute("""
                SELECT id, avg_prep_time 
                FROM kitchen_kitchenperformance
            """)
            
            rows = cursor.fetchall()
            fixed_count = 0
            
            for row_id, avg_prep_time in rows:
                if avg_prep_time is None or avg_prep_time == '':
                    # Set NULL/empty to 0.00
                    cursor.execute(
                        "UPDATE kitchen_kitchenperformance SET avg_prep_time = ? WHERE id = ?",
                        ['0.00', row_id]
                    )
                    fixed_count += 1
                    self.stdout.write(f"  Fixed NULL/empty in row {row_id}")
                else:
                    try:
                        # Try to parse as number (may be integer or string)
                        value = float(avg_prep_time)
                        # Convert to proper decimal format (2 decimal places)
                        new_value = f"{value:.2f}"
                        
                        # Update with properly formatted decimal
                        cursor.execute(
                            "UPDATE kitchen_kitchenperformance SET avg_prep_time = ? WHERE id = ?",
                            [new_value, row_id]
                        )
                        fixed_count += 1
                        self.stdout.write(f"  Fixed row {row_id}: {avg_prep_time} -> {new_value}")
                    except (ValueError, TypeError, InvalidOperation) as e:
                        self.stdout.write(self.style.WARNING(f"  Could not convert row {row_id}: {avg_prep_time} ({e})"))
                        # Set to 0.00 if can't convert
                        cursor.execute(
                            "UPDATE kitchen_kitchenperformance SET avg_prep_time = ? WHERE id = ?",
                            ['0.00', row_id]
                        )
                        fixed_count += 1
            
        self.stdout.write(self.style.SUCCESS(f'✅ Fixed {fixed_count} rows'))
        self.stdout.write(self.style.SUCCESS('✅ KitchenPerformance data cleaned'))
