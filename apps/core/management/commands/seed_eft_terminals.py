"""
Seed default EFT Terminal master data.
Based on backoffice EFT ID Lists reference.

Usage: python manage.py seed_eft_terminals
"""
from django.core.management.base import BaseCommand
from apps.core.models import Company, EFTTerminal


DEFAULT_EFT_TERMINALS = [
    {'code': '01', 'name': 'BCA', 'sort_order': 1},
    {'code': '02', 'name': 'CITIBANK', 'sort_order': 2},
    {'code': '03', 'name': 'BNI', 'sort_order': 3},
    {'code': '04', 'name': 'BRI', 'sort_order': 4},
    {'code': '05', 'name': 'PERMATA', 'sort_order': 5},
    {'code': '06', 'name': 'BANK MEGA', 'sort_order': 6},
    {'code': '07', 'name': 'MANDIRI', 'sort_order': 7},
    {'code': '08', 'name': 'NIAGA', 'sort_order': 8},
    {'code': '09', 'name': 'E-MONEY', 'sort_order': 9},
    {'code': '10', 'name': 'OTHER', 'sort_order': 10},
]


class Command(BaseCommand):
    help = 'Seed default EFT Terminal master data (bank codes for card payments)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing EFT terminals')

    def handle(self, *args, **options):
        force = options.get('force', False)

        companies = Company.objects.filter(is_active=True)
        if not companies.exists():
            self.stderr.write('No active companies found.')
            return

        for company in companies:
            self.stdout.write(f'\nSeeding EFT terminals for company: {company.name}')

            for eft_data in DEFAULT_EFT_TERMINALS:
                existing = EFTTerminal.objects.filter(
                    company=company, code=eft_data['code']
                ).first()

                if existing and not force:
                    self.stdout.write(f'  Skipped (exists): {eft_data["code"]}: {eft_data["name"]}')
                    continue

                if existing and force:
                    existing.name = eft_data['name']
                    existing.sort_order = eft_data['sort_order']
                    existing.save()
                    self.stdout.write(f'  Updated: {eft_data["code"]}: {eft_data["name"]}')
                else:
                    EFTTerminal.objects.create(
                        company=company,
                        code=eft_data['code'],
                        name=eft_data['name'],
                        sort_order=eft_data['sort_order'],
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f'  Created: {eft_data["code"]}: {eft_data["name"]}'
                    ))

        self.stdout.write(self.style.SUCCESS('\nDone seeding EFT terminals.'))
