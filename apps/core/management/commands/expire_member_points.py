"""
Management command to expire member points based on company/brand policy.

Usage:
    python manage.py expire_member_points
    python manage.py expire_member_points --dry-run
    python manage.py expire_member_points --company=YGY
    python manage.py expire_member_points --brand=AYAMGEPREK

Schedule this command to run daily via cron/task scheduler:
    # Linux/Mac cron (daily at 2am)
    0 2 * * * cd /path/to/pos && python manage.py expire_member_points
    
    # Windows Task Scheduler (daily at 2am)
    Action: Start a program
    Program: python
    Arguments: manage.py expire_member_points
    Start in: D:\\YOGYA-Kiosk\\pos-django-htmx-main
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from decimal import Decimal
from apps.core.models import Company, Member, MemberTransaction


class Command(BaseCommand):
    help = 'Expire member points based on company/brand point expiry policy'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be expired without actually expiring',
        )
        parser.add_argument(
            '--company',
            type=str,
            help='Process only specific company code',
        )
        parser.add_argument(
            '--brand',
            type=str,
            help='Process only specific brand code',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        company_code = options.get('company')
        brand_code = options.get('brand')
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('MEMBER POINTS EXPIRY SCHEDULER'))
        self.stdout.write(self.style.SUCCESS(f'Started: {timezone.now()}'))
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Filter companies
        companies = Company.objects.filter(is_active=True)
        if company_code:
            companies = companies.filter(code=company_code)
        
        total_members_processed = 0
        total_points_expired = 0
        total_transactions_created = 0
        
        for company in companies:
            self.stdout.write(f'\nProcessing Company: {company.name} ({company.code})')
            self.stdout.write(f'  Point Expiry Policy: {company.point_expiry_months} months')
            
            # Skip if expiry disabled
            if company.point_expiry_months == 0:
                self.stdout.write(self.style.WARNING('  ⊗ Points never expire (policy = 0 months)'))
                continue
            
            # Calculate expiry date
            expiry_date = timezone.now() - timedelta(days=company.point_expiry_months * 30)
            self.stdout.write(f'  Expiring points earned before: {expiry_date.date()}')
            
            # Get members with expirable points
            members = Member.objects.filter(
                company=company,
                is_active=True,
                points__gt=0
            )
            
            if brand_code:
                # Filter by brand if specified (though member is company-level)
                self.stdout.write(f'  Filtering by brand: {brand_code}')
            
            members_with_expired = 0
            
            for member in members:
                # Get oldest earn transactions that are still contributing to current points
                old_earn_transactions = MemberTransaction.objects.filter(
                    member=member,
                    transaction_type='earn',
                    created_at__lt=expiry_date,
                    points_change__gt=0
                ).order_by('created_at')
                
                if not old_earn_transactions.exists():
                    continue
                
                # Calculate total expired points
                expired_points = sum(
                    tx.points_change for tx in old_earn_transactions
                    if tx.points_change > 0
                )
                
                # Don't expire more points than member currently has
                expired_points = min(expired_points, member.points)
                
                if expired_points <= 0:
                    continue
                
                members_with_expired += 1
                total_points_expired += expired_points
                
                self.stdout.write(
                    f'    • {member.member_code} ({member.full_name}): '
                    f'{expired_points} points to expire '
                    f'(current: {member.points}, after: {member.points - expired_points})'
                )
                
                if not dry_run:
                    # Create expiry transaction
                    with transaction.atomic():
                        # Lock member row for update
                        member = Member.objects.select_for_update().get(pk=member.pk)
                        
                        points_before = member.points
                        points_after = points_before - expired_points
                        
                        # Create expiry transaction
                        MemberTransaction.objects.create(
                            member=member,
                            transaction_type='expired',
                            points_change=-expired_points,
                            balance_change=Decimal('0.00'),
                            points_before=points_before,
                            points_after=points_after,
                            balance_before=member.point_balance,
                            balance_after=member.point_balance,
                            reference=f'Auto-expired after {company.point_expiry_months} months',
                            notes=f'Points earned before {expiry_date.date()} expired automatically',
                            created_by=None  # System-generated
                        )
                        
                        # Update member points
                        member.points = points_after
                        member.save(update_fields=['points'])
                        
                        total_transactions_created += 1
            
            total_members_processed += members.count()
            
            self.stdout.write(
                f'  ✓ Processed {members_with_expired} members with expired points '
                f'out of {members.count()} total members'
            )
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Total members processed: {total_members_processed}')
        self.stdout.write(f'Total points expired: {total_points_expired}')
        self.stdout.write(f'Total transactions created: {total_transactions_created}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - No changes were made to the database'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ All expiry transactions committed to database'))
        
        self.stdout.write(self.style.SUCCESS(f'\nCompleted: {timezone.now()}'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
