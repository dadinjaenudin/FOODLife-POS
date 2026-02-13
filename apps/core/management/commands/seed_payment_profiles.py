"""
Seed default PaymentMethodProfile and DataEntryPrompt records.
Matches the backoffice keyboard mapping configuration.

Usage: python manage.py seed_payment_profiles
"""
from django.core.management.base import BaseCommand
from apps.core.models import (
    Company, Brand, MediaGroup, PaymentMethodProfile, DataEntryPrompt,
)


MEDIA_GROUPS = [
    {'code': 'cash', 'name': 'Cash', 'orafin_group': 'Cash'},
    {'code': 'credit_card', 'name': 'Credit Card Group', 'orafin_group': 'Credit Card'},
    {'code': 'debit_card', 'name': 'Debit Card Group', 'orafin_group': 'Credit Card'},
    {'code': 'online_payment', 'name': 'Online Payment', 'orafin_group': 'Credit Card'},
    {'code': 'qris', 'name': 'QRIS', 'orafin_group': 'Credit Card'},
    {'code': 'voucher', 'name': 'Voucher Group', 'orafin_group': 'Yogya Voucher'},
]

PROFILES = [
    {
        'code': 'cash',
        'name': 'Cash',
        'media_group_code': 'cash',
        'media_id': 1,
        'color': '#16a34a',
        'legacy_method_id': 'cash',
        'allow_change': True,
        'open_cash_drawer': True,
        'smallest_denomination': 0,
        'sort_order': 1,
        'prompts': [
            {'field_name': 'amount', 'label': 'Amount', 'field_type': 'amount', 'min_length': 0, 'max_length': 99, 'placeholder': 'Enter amount', 'sort_order': 0},
        ],
    },
    {
        'code': 'credit_card',
        'name': 'Credit Card',
        'media_group_code': 'credit_card',
        'media_id': 26,
        'color': '#2563eb',
        'legacy_method_id': 'card',
        'allow_change': False,
        'open_cash_drawer': False,
        'smallest_denomination': 50000,
        'sort_order': 2,
        'prompts': [
            {'field_name': 'amount', 'label': 'Amount', 'field_type': 'amount', 'min_length': 0, 'max_length': 99, 'placeholder': 'Enter amount', 'sort_order': 0},
            {'field_name': 'account_no', 'label': 'Account No', 'field_type': 'numeric', 'min_length': 6, 'max_length': 6, 'placeholder': 'Input account number', 'is_required': True, 'sort_order': 1},
            {'field_name': 'eft_no', 'label': 'EFT No', 'field_type': 'numeric', 'min_length': 2, 'max_length': 2, 'placeholder': 'Input EFT Terminal', 'is_required': True, 'sort_order': 2},
            {'field_name': 'approval_code', 'label': 'Approval Code', 'field_type': 'numeric', 'min_length': 5, 'max_length': 6, 'placeholder': 'Input approval code', 'is_required': True, 'sort_order': 3},
        ],
    },
    {
        'code': 'debit_card',
        'name': 'Debit Card',
        'media_group_code': 'debit_card',
        'media_id': 27,
        'color': '#9333ea',
        'legacy_method_id': 'debit',
        'allow_change': False,
        'open_cash_drawer': False,
        'smallest_denomination': 0,
        'sort_order': 3,
        'prompts': [
            {'field_name': 'amount', 'label': 'Amount', 'field_type': 'amount', 'min_length': 0, 'max_length': 99, 'placeholder': 'Enter amount', 'sort_order': 0},
            {'field_name': 'account_no', 'label': 'Account No', 'field_type': 'numeric', 'min_length': 6, 'max_length': 6, 'placeholder': 'Input account number', 'is_required': True, 'sort_order': 1},
            {'field_name': 'eft_no', 'label': 'EFT No', 'field_type': 'numeric', 'min_length': 2, 'max_length': 2, 'placeholder': 'Input EFT Terminal', 'is_required': True, 'sort_order': 2},
            {'field_name': 'approval_code', 'label': 'Approval Code', 'field_type': 'numeric', 'min_length': 4, 'max_length': 6, 'placeholder': 'Input approval code', 'is_required': True, 'sort_order': 3},
        ],
    },
    {
        'code': 'dana',
        'name': 'DANA',
        'media_group_code': 'online_payment',
        'media_id': 15,
        'color': '#0891b2',
        'legacy_method_id': 'ewallet',
        'allow_change': False,
        'open_cash_drawer': False,
        'smallest_denomination': 0,
        'sort_order': 4,
        'prompts': [
            {'field_name': 'amount', 'label': 'Amount', 'field_type': 'amount', 'min_length': 0, 'max_length': 99, 'placeholder': 'Enter amount', 'sort_order': 0},
            {'field_name': 'eft_no', 'label': 'EFT No', 'field_type': 'numeric', 'min_length': 2, 'max_length': 2, 'placeholder': 'Input EFT Terminal', 'is_required': True, 'sort_order': 1},
            {'field_name': 'approval_code', 'label': 'Approval Code', 'field_type': 'numeric', 'min_length': 4, 'max_length': 6, 'placeholder': 'Input approval code', 'is_required': True, 'sort_order': 2},
        ],
    },
    {
        'code': 'yogya_voucher',
        'name': 'YOGYA VOUCHER',
        'media_group_code': 'voucher',
        'media_id': 2,
        'color': '#ea580c',
        'legacy_method_id': 'voucher',
        'allow_change': False,
        'open_cash_drawer': False,
        'smallest_denomination': 0,
        'sort_order': 5,
        'prompts': [
            {'field_name': 'amount', 'label': 'Amount', 'field_type': 'amount', 'min_length': 0, 'max_length': 99, 'placeholder': 'Input amount', 'sort_order': 0},
        ],
    },
    {
        'code': 'qris_bca_cpm',
        'name': 'QRIS BCA CPM',
        'media_group_code': 'qris',
        'media_id': 33,
        'color': '#7c3aed',
        'legacy_method_id': 'qris',
        'allow_change': False,
        'open_cash_drawer': False,
        'smallest_denomination': 0,
        'sort_order': 6,
        'prompts': [
            {'field_name': 'amount', 'label': 'Amount', 'field_type': 'amount', 'min_length': 0, 'max_length': 9, 'placeholder': 'Input amount', 'sort_order': 0},
            {'field_name': 'qrcontent', 'label': 'QR Content', 'field_type': 'scanner', 'min_length': 0, 'max_length': 99, 'placeholder': 'Please scan qr', 'use_scanner': True, 'sort_order': 1},
        ],
    },
    {
        'code': 'qris_mandiri_mpm',
        'name': 'QRIS Mandiri MPM',
        'media_group_code': 'qris',
        'media_id': 32,
        'color': '#7c3aed',
        'legacy_method_id': 'qris',
        'allow_change': False,
        'open_cash_drawer': False,
        'smallest_denomination': 0,
        'sort_order': 7,
        'prompts': [
            {'field_name': 'amount', 'label': 'Amount', 'field_type': 'amount', 'min_length': 0, 'max_length': 8, 'placeholder': 'Input amount', 'use_scanner': True, 'sort_order': 0},
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed default payment method profiles and data entry prompts'

    def add_arguments(self, parser):
        parser.add_argument('--brand', type=str, help='Specific brand code to seed for')
        parser.add_argument('--force', action='store_true', help='Overwrite existing profiles')

    def handle(self, *args, **options):
        brand_code = options.get('brand')
        force = options.get('force', False)

        companies = Company.objects.filter(is_active=True)
        if not companies.exists():
            self.stderr.write('No active companies found.')
            return

        for company in companies:
            # Create media groups
            mg_map = {}
            for mg_data in MEDIA_GROUPS:
                mg, created = MediaGroup.objects.get_or_create(
                    company=company,
                    code=mg_data['code'],
                    defaults={
                        'name': mg_data['name'],
                        'orafin_group': mg_data['orafin_group'],
                    }
                )
                mg_map[mg_data['code']] = mg
                if created:
                    self.stdout.write(f'  Created MediaGroup: {mg.name}')

            # Get brands
            brands = Brand.objects.filter(company=company, is_active=True)
            if brand_code:
                brands = brands.filter(code=brand_code)

            for brand in brands:
                self.stdout.write(f'\nSeeding profiles for brand: {brand.name}')

                for p_data in PROFILES:
                    existing = PaymentMethodProfile.objects.filter(brand=brand, code=p_data['code']).first()

                    if existing and not force:
                        self.stdout.write(f'  Skipped (exists): {p_data["name"]}')
                        continue

                    if existing and force:
                        existing.prompts.all().delete()
                        existing.delete()

                    profile = PaymentMethodProfile.objects.create(
                        company=company,
                        brand=brand,
                        media_group=mg_map.get(p_data['media_group_code']),
                        media_id=p_data['media_id'],
                        name=p_data['name'],
                        code=p_data['code'],
                        color=p_data['color'],
                        legacy_method_id=p_data['legacy_method_id'],
                        allow_change=p_data['allow_change'],
                        open_cash_drawer=p_data['open_cash_drawer'],
                        smallest_denomination=p_data['smallest_denomination'],
                        sort_order=p_data['sort_order'],
                    )

                    for prompt_data in p_data['prompts']:
                        DataEntryPrompt.objects.create(
                            profile=profile,
                            field_name=prompt_data['field_name'],
                            label=prompt_data['label'],
                            field_type=prompt_data['field_type'],
                            min_length=prompt_data['min_length'],
                            max_length=prompt_data['max_length'],
                            placeholder=prompt_data.get('placeholder', ''),
                            use_scanner=prompt_data.get('use_scanner', False),
                            is_required=prompt_data.get('is_required', False),
                            sort_order=prompt_data['sort_order'],
                        )

                    self.stdout.write(self.style.SUCCESS(
                        f'  Created: {profile.name} ({len(p_data["prompts"])} prompts)'
                    ))

        self.stdout.write(self.style.SUCCESS('\nDone seeding payment profiles.'))
