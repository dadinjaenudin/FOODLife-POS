"""
Management command to create a superuser with custom User model

This handles the Company and Brand foreign keys required by the custom User model.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import User, Company, Brand


class Command(BaseCommand):
    help = 'Create a superuser with Company and Brand'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username for superuser')
        parser.add_argument('--email', type=str, help='Email for superuser')
        parser.add_argument('--password', type=str, help='Password for superuser')
        parser.add_argument('--pin', type=str, default='123456', help='PIN for superuser (default: 123456)')

    def handle(self, *args, **options):
        username = options.get('username') or input('Username: ')
        email = options.get('email') or input('Email: ')
        password = options.get('password') or input('Password: ')
        pin = options.get('pin') or '123456'

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User "{username}" already exists!'))
            return

        # Get or create Company
        company = Company.objects.first()
        if not company:
            self.stdout.write(self.style.WARNING('No company found. Creating default company...'))
            company = Company.objects.create(
                code='YGY',
                name='Yogya Group',
                timezone='Asia/Jakarta',
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f'Created company: {company.name}'))

        # Get or create Brand
        brand = Brand.objects.filter(company=company).first()
        if not brand:
            self.stdout.write(self.style.WARNING('No brand found. Creating default brand...'))
            brand = Brand.objects.create(
                company=company,
                code='YGY-001',
                name='Head Office',
                tax_rate=11.00,
                service_charge=0.00,
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f'Created brand: {brand.name}'))

        # Create superuser
        try:
            with transaction.atomic():
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    company=company,
                    brand=brand,
                    role='admin',
                    role_scope='company',
                    pin=pin,
                    is_staff=True,
                    is_superuser=True
                )
                
                self.stdout.write(self.style.SUCCESS('\n' + '='*60))
                self.stdout.write(self.style.SUCCESS('✅ SUPERUSER CREATED SUCCESSFULLY'))
                self.stdout.write(self.style.SUCCESS('='*60))
                self.stdout.write(f'Username: {user.username}')
                self.stdout.write(f'Email: {user.email}')
                self.stdout.write(f'Company: {user.company.name}')
                self.stdout.write(f'Brand: {user.brand.name}')
                self.stdout.write(f'Role: {user.role} (scope: {user.role_scope})')
                self.stdout.write(f'PIN: {user.pin}')
                self.stdout.write(self.style.SUCCESS('='*60))
                self.stdout.write(self.style.WARNING('\n🔐 Keep this information secure!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}'))
