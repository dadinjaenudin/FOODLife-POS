"""
EOD (End of Day) Service

Handles:
- EOD validation and execution
- Automatic EOD overdue detection
- Force EOD with supervisor approval
- EOD checklist management
"""
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from datetime import timedelta
from decimal import Decimal


class EODService:
    """Service for End of Day operations"""
    
    EOD_CHECKLIST_ITEMS = [
        "Verify all bills are closed or voided",
        "Check kitchen has no pending orders",
        "All cashier shifts are closed",
        "Cash drawer counted and recorded",
        "Print Z-Report (daily summary)",
        "Backup database",
        "Lock safe / secure cash",
        "Check and clean POS terminals",
    ]
    
    OVERDUE_WARNING_HOURS = 12
    OVERDUE_CRITICAL_HOURS = 24
    
    @staticmethod
    def check_eod_status(store):
        """
        Check current EOD status for store
        
        Returns:
            dict with status info
        """
        from apps.core.models_session import StoreSession, BusinessDateAlert
        
        current_session = StoreSession.get_current(store)
        
        if not current_session:
            return {
                'status': 'no_session',
                'message': 'No active session found. Please create a new session.',
                'severity': 'critical',
                'can_transact': False,
            }
        
        hours_open = current_session.hours_since_open()
        
        if hours_open > EODService.OVERDUE_CRITICAL_HOURS:
            # Critical - create alert
            BusinessDateAlert.create_eod_overdue_alert(store, current_session)
            return {
                'status': 'critical_overdue',
                'message': f'EOD is {hours_open:.1f} hours overdue! Transactions locked.',
                'severity': 'critical',
                'can_transact': False,
                'hours_open': hours_open,
                'session': current_session,
            }
        
        elif hours_open > EODService.OVERDUE_WARNING_HOURS:
            return {
                'status': 'warning_overdue',
                'message': f'EOD is overdue ({hours_open:.1f} hours). Please close day soon.',
                'severity': 'warning',
                'can_transact': True,
                'hours_open': hours_open,
                'session': current_session,
            }
        
        else:
            return {
                'status': 'ok',
                'message': 'Session active and healthy',
                'severity': 'info',
                'can_transact': True,
                'hours_open': hours_open,
                'session': current_session,
            }
    
    @staticmethod
    @transaction.atomic
    def create_eod_checklist(session, created_by):
        """
        Create EOD checklist for session
        
        Args:
            session: StoreSession object
            created_by: User who creates checklist
        
        Returns:
            List of EODChecklist objects
        """
        from apps.core.models_session import EODChecklist
        
        checklist_items = []
        for item_text in EODService.EOD_CHECKLIST_ITEMS:
            item = EODChecklist.objects.create(
                store_session=session,
                checklist_item=item_text,
            )
            checklist_items.append(item)
        
        return checklist_items
    
    @staticmethod
    def validate_eod_readiness(session):
        """
        Validate if session is ready for EOD
        
        Returns:
            dict with validation results
        """
        from apps.pos.models import Bill
        from apps.core.models_session import CashierShift
        from apps.kitchen.models import KitchenOrder
        
        issues = []
        warnings = []
        
        # Check open bills
        open_bills = Bill.objects.filter(
            business_date=session.business_date,
            status='open'
        ).count()
        
        if open_bills > 0:
            issues.append(f"{open_bills} bill(s) still open")
        
        # Check held bills
        held_bills = Bill.objects.filter(
            business_date=session.business_date,
            status='hold'
        ).count()
        
        if held_bills > 0:
            warnings.append(f"{held_bills} bill(s) on hold")
        
        # Check open cashier shifts
        open_shifts = CashierShift.objects.filter(
            store_session=session,
            status='open'
        ).count()
        
        if open_shifts > 0:
            issues.append(f"{open_shifts} cashier shift(s) still open")
        
        # Check pending kitchen orders
        pending_kitchen = KitchenOrder.objects.filter(
            bill__business_date=session.business_date,
            status__in=['pending', 'preparing']
        ).count()
        
        if pending_kitchen > 0:
            warnings.append(f"{pending_kitchen} kitchen order(s) still pending")
        
        # Check checklist completion
        from apps.core.models_session import EODChecklist
        checklist_items = EODChecklist.objects.filter(store_session=session)
        
        if checklist_items.exists():
            incomplete = checklist_items.filter(is_completed=False).count()
            if incomplete > 0:
                warnings.append(f"{incomplete} checklist item(s) not completed")
        
        return {
            'can_proceed': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'total_issues': len(issues),
            'total_warnings': len(warnings),
        }
    
    @staticmethod
    @transaction.atomic
    def execute_eod(session, closed_by, notes='', force=False):
        """
        Execute End of Day process
        
        Args:
            session: StoreSession object to close
            closed_by: User performing EOD
            notes: EOD notes/remarks
            force: Force EOD even with open items
        
        Returns:
            New StoreSession object for next business date
        """
        # Validate readiness
        validation = EODService.validate_eod_readiness(session)
        
        if not validation['can_proceed'] and not force:
            raise ValidationError(
                f"Cannot execute EOD. Issues: {', '.join(validation['issues'])}"
            )
        
        # Generate EOD report before closing
        eod_report = EODService.generate_eod_report(session)
        
        # Close session and create next
        next_session = session.close(closed_by=closed_by, notes=notes, force=force)
        
        # Create checklist for next session
        EODService.create_eod_checklist(next_session, closed_by)
        
        # Log EOD completion
        from apps.pos.models import BillLog
        BillLog.objects.create(
            bill=None,  # Session-level log
            action='eod_completed',
            details={
                'session_id': str(session.id),
                'business_date': str(session.business_date),
                'next_session_id': str(next_session.id),
                'next_business_date': str(next_session.business_date),
                'forced': force,
                'report': eod_report,
            },
            user=closed_by,
        )
        
        return next_session
    
    @staticmethod
    def generate_eod_report(session):
        """
        Generate comprehensive EOD report
        
        Returns:
            dict with EOD summary
        """
        from apps.pos.models import Bill, Payment
        from apps.core.models_session import CashierShift
        
        # Bills summary
        bills = Bill.objects.filter(business_date=session.business_date)
        paid_bills = bills.filter(status='paid')
        
        # Payment summary by method
        payments = Payment.objects.filter(bill__business_date=session.business_date)
        payment_summary = payments.values('method').annotate(
            total=models.Sum('amount'),
            count=models.Count('id')
        )
        
        # Cashier shift summary
        shifts = CashierShift.objects.filter(store_session=session)
        total_cash_variance = sum(
            shift.cash_difference for shift in shifts.filter(status='closed')
        )
        
        report = {
            'session': {
                'id': str(session.id),
                'business_date': str(session.business_date),
                'opened_at': session.opened_at.isoformat(),
                'hours_open': session.hours_since_open(),
            },
            'bills': {
                'total_count': bills.count(),
                'paid_count': paid_bills.count(),
                'total_amount': str(paid_bills.aggregate(total=models.Sum('total'))['total'] or Decimal('0')),
                'average_bill': str(paid_bills.aggregate(avg=models.Avg('total'))['avg'] or Decimal('0')),
            },
            'payments': {
                'total_amount': str(payments.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')),
                'total_count': payments.count(),
                'by_method': [
                    {
                        'method': p['method'],
                        'total': str(p['total']),
                        'count': p['count'],
                    }
                    for p in payment_summary
                ],
            },
            'shifts': {
                'total_count': shifts.count(),
                'closed_count': shifts.filter(status='closed').count(),
                'total_cash_variance': str(total_cash_variance),
            },
        }
        
        return report
    
    @staticmethod
    def get_pending_eod_sessions():
        """
        Get all sessions that need EOD (overdue)
        
        Returns:
            QuerySet of overdue sessions
        """
        from apps.core.models_session import StoreSession
        
        threshold = timezone.now() - timedelta(hours=EODService.OVERDUE_WARNING_HOURS)
        
        return StoreSession.objects.filter(
            status='open',
            is_current=True,
            opened_at__lt=threshold
        )


from django.db import models

class ShiftService:
    """Service for cashier shift operations"""
    
    @staticmethod
    @transaction.atomic
    def open_shift(cashier, terminal, opening_cash=Decimal('0')):
        """
        Open new cashier shift
        
        Args:
            cashier: User object (cashier)
            terminal: POSTerminal object
            opening_cash: Starting cash amount
        
        Returns:
            CashierShift object
        """
        from apps.core.models_session import StoreSession, CashierShift
        
        # Get current session
        store = terminal.store
        current_session = StoreSession.get_current(store)
        
        if not current_session:
            raise ValidationError("No active session. Please start a new business day first.")
        
        # Check if cashier already has open shift
        existing_shift = CashierShift.objects.filter(
            cashier=cashier,
            status='open'
        ).first()
        
        if existing_shift:
            raise ValidationError(f"Cashier already has an open shift on terminal {existing_shift.terminal.terminal_code}")
        
        # Create new shift
        shift = CashierShift.objects.create(
            store_session=current_session,
            cashier=cashier,
            terminal=terminal,
            opening_cash=opening_cash,
        )
        
        return shift
    
    @staticmethod
    @transaction.atomic
    def close_shift(shift, actual_amounts, closed_by, notes=''):
        """
        Close cashier shift with payment reconciliation
        
        Args:
            shift: CashierShift object
            actual_amounts: dict of {payment_method: actual_amount}
            closed_by: User who approves close (can be cashier or supervisor)
            notes: Closing notes
        
        Returns:
            dict with reconciliation summary
        """
        from apps.core.models_session import ShiftPaymentSummary, BusinessDateAlert
        from apps.pos.models import Payment
        
        if shift.status != 'open':
            raise ValidationError("Shift is already closed")
        
        # Calculate actual cash
        actual_cash = actual_amounts.get('cash', Decimal('0'))
        
        # Close shift
        cash_difference = shift.close_shift(actual_cash, closed_by, notes)
        
        # Create payment summaries
        summaries = []
        for method, actual_amount in actual_amounts.items():
            summary = ShiftPaymentSummary.objects.create(
                cashier_shift=shift,
                payment_method=method,
                actual_amount=actual_amount,
            )
            summary.calculate_expected()
            summaries.append(summary)
        
        # Check for significant variance
        variance_threshold = Decimal('50000')  # Rp 50,000
        if abs(cash_difference) > variance_threshold:
            BusinessDateAlert.create_cash_variance_alert(shift.terminal.store, shift)
        
        return {
            'shift': shift,
            'cash_difference': cash_difference,
            'payment_summaries': summaries,
            'requires_approval': abs(cash_difference) > variance_threshold,
        }
