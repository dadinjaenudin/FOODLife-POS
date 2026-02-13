"""
Payment Gateway Abstraction Layer

Provides a pluggable interface for QRIS payment processing.
Currently implements MockQRISGateway for development.
Swap to real gateway (Midtrans/Xendit) by changing PAYMENT_GATEWAY setting.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
import logging
import uuid

logger = logging.getLogger('pos.qris')


def _audit_log(event, txn_ref='', bill=None, transaction=None, amount=None,
               status_before='', status_after='', gateway_name='',
               response_time_ms=None, elapsed_since_create_s=None,
               error_message='', extra_data=None, user=None, ip_address=None):
    """Write a row to QRISAuditLog table. Non-blocking — errors are logged, not raised."""
    try:
        from .models import QRISAuditLog
        QRISAuditLog.objects.create(
            event=event,
            txn_ref=txn_ref,
            bill=bill,
            transaction=transaction,
            amount=amount,
            status_before=status_before,
            status_after=status_after,
            gateway_name=gateway_name,
            response_time_ms=response_time_ms,
            elapsed_since_create_s=elapsed_since_create_s,
            error_message=error_message,
            extra_data=extra_data or {},
            user=user,
            ip_address=ip_address,
        )
    except Exception as e:
        logger.error('QRIS_AUDIT_LOG_FAILED event=%s txn_ref=%s error=%s', event, txn_ref, e)


@dataclass
class QRISCreateResult:
    success: bool
    transaction_id: str = ''
    qr_string: str = ''
    qr_url: str = ''
    expires_at: Optional[object] = None
    error_message: str = ''


@dataclass
class QRISStatusResult:
    status: str  # pending, paid, expired, failed, cancelled
    transaction_id: str = ''
    paid_at: Optional[object] = None
    error_message: str = ''


class PaymentGateway(ABC):
    """Abstract base class for payment gateways."""

    @abstractmethod
    def create_qris_transaction(self, bill, amount: Decimal, **kwargs) -> QRISCreateResult:
        """Create a QRIS transaction and return QR code data."""
        pass

    @abstractmethod
    def check_status(self, transaction_id: str) -> QRISStatusResult:
        """Check the status of a QRIS transaction."""
        pass

    @abstractmethod
    def cancel_transaction(self, transaction_id: str) -> bool:
        """Cancel a pending QRIS transaction."""
        pass


class MockQRISGateway(PaymentGateway):
    """
    Mock QRIS gateway for development/testing.
    Stores state in QRISTransaction model.
    Use "Simulate Payment" button in frontend to mark as paid.
    """

    def create_qris_transaction(self, bill, amount: Decimal, **kwargs) -> QRISCreateResult:
        from .models import QRISTransaction

        timeout_minutes = getattr(settings, 'QRIS_TIMEOUT_MINUTES', 5)
        expires_at = timezone.now() + timezone.timedelta(minutes=timeout_minutes)
        transaction_id = f"MOCK-{uuid.uuid4().hex[:12].upper()}"

        # Generate a mock QR string (in production this comes from gateway)
        qr_string = f"00020101021226610014ID.CO.MOCK.WWW0118{transaction_id}5303360540{int(amount)}5802ID6015FOODLIFE POS63041234"

        txn = QRISTransaction.objects.create(
            bill=bill,
            transaction_id=transaction_id,
            amount=amount,
            qr_string=qr_string,
            status='pending',
            gateway_name='mock',
            expires_at=expires_at,
            created_by=kwargs.get('user'),
        )

        logger.info(
            'QRIS_CREATE bill=%s txn_id=%s amount=%s gateway=mock expires_at=%s user=%s',
            bill.id, transaction_id, amount, expires_at.isoformat(),
            kwargs.get('user'),
        )

        _audit_log(
            event='create',
            txn_ref=transaction_id,
            bill=bill,
            transaction=txn,
            amount=amount,
            status_after='pending',
            gateway_name='mock',
            user=kwargs.get('user'),
            extra_data={'expires_at': expires_at.isoformat()},
        )

        return QRISCreateResult(
            success=True,
            transaction_id=transaction_id,
            qr_string=qr_string,
            expires_at=expires_at,
        )

    def check_status(self, transaction_id: str) -> QRISStatusResult:
        from .models import QRISTransaction

        try:
            txn = QRISTransaction.objects.get(transaction_id=transaction_id)
        except QRISTransaction.DoesNotExist:
            logger.warning('QRIS_STATUS_NOT_FOUND txn_id=%s', transaction_id)
            _audit_log(
                event='error',
                txn_ref=transaction_id,
                error_message='Transaction not found on status check',
            )
            return QRISStatusResult(
                status='failed',
                transaction_id=transaction_id,
                error_message='Transaction not found',
            )

        prev_status = txn.status

        # Check if expired
        if txn.status == 'pending' and txn.expires_at and timezone.now() > txn.expires_at:
            txn.status = 'expired'
            txn.save(update_fields=['status'])
            elapsed = (timezone.now() - txn.created_at).total_seconds()
            logger.info(
                'QRIS_EXPIRED txn_id=%s bill=%s amount=%s elapsed=%.1fs timeout=%s',
                txn.transaction_id, txn.bill_id, txn.amount, elapsed, txn.expires_at.isoformat(),
            )
            _audit_log(
                event='expired',
                txn_ref=txn.transaction_id,
                bill=txn.bill,
                transaction=txn,
                amount=txn.amount,
                status_before='pending',
                status_after='expired',
                gateway_name=txn.gateway_name,
                elapsed_since_create_s=elapsed,
            )

        # Log status transitions (paid, expired, failed, cancelled)
        if txn.status != 'pending' and prev_status == 'pending':
            elapsed = (timezone.now() - txn.created_at).total_seconds()
            event_type = 'payment_confirmed' if txn.status == 'paid' else 'status_change'
            logger.info(
                'QRIS_STATUS_CHANGE txn_id=%s bill=%s status=%s prev=%s amount=%s '
                'elapsed=%.1fs paid_at=%s gateway=%s',
                txn.transaction_id, txn.bill_id, txn.status, prev_status,
                txn.amount, elapsed,
                txn.paid_at.isoformat() if txn.paid_at else None,
                txn.gateway_name,
            )
            _audit_log(
                event=event_type,
                txn_ref=txn.transaction_id,
                bill=txn.bill,
                transaction=txn,
                amount=txn.amount,
                status_before=prev_status,
                status_after=txn.status,
                gateway_name=txn.gateway_name,
                elapsed_since_create_s=elapsed,
                extra_data={'paid_at': txn.paid_at.isoformat() if txn.paid_at else None},
            )

        return QRISStatusResult(
            status=txn.status,
            transaction_id=txn.transaction_id,
            paid_at=txn.paid_at,
        )

    def cancel_transaction(self, transaction_id: str) -> bool:
        from .models import QRISTransaction

        try:
            txn = QRISTransaction.objects.get(transaction_id=transaction_id, status='pending')
            elapsed = (timezone.now() - txn.created_at).total_seconds()
            txn.status = 'cancelled'
            txn.save(update_fields=['status'])
            logger.info(
                'QRIS_CANCELLED txn_id=%s bill=%s amount=%s elapsed=%.1fs',
                txn.transaction_id, txn.bill_id, txn.amount, elapsed,
            )
            _audit_log(
                event='cancelled',
                txn_ref=txn.transaction_id,
                bill=txn.bill,
                transaction=txn,
                amount=txn.amount,
                status_before='pending',
                status_after='cancelled',
                gateway_name=txn.gateway_name,
                elapsed_since_create_s=elapsed,
            )
            return True
        except QRISTransaction.DoesNotExist:
            logger.warning('QRIS_CANCEL_NOT_FOUND txn_id=%s', transaction_id)
            _audit_log(
                event='error',
                txn_ref=transaction_id,
                error_message='Cancel failed — transaction not found or not pending',
            )
            return False

    def simulate_payment(self, transaction_id: str) -> bool:
        """DEV ONLY: Simulate a successful QRIS payment."""
        from .models import QRISTransaction

        try:
            txn = QRISTransaction.objects.get(transaction_id=transaction_id, status='pending')
            elapsed = (timezone.now() - txn.created_at).total_seconds()
            txn.status = 'paid'
            txn.paid_at = timezone.now()
            txn.gateway_response = {'simulated': True, 'paid_at': str(timezone.now())}
            txn.save(update_fields=['status', 'paid_at', 'gateway_response'])
            logger.info(
                'QRIS_SIMULATED txn_id=%s bill=%s amount=%s elapsed=%.1fs paid_at=%s',
                txn.transaction_id, txn.bill_id, txn.amount, elapsed, txn.paid_at.isoformat(),
            )
            _audit_log(
                event='simulate',
                txn_ref=txn.transaction_id,
                bill=txn.bill,
                transaction=txn,
                amount=txn.amount,
                status_before='pending',
                status_after='paid',
                gateway_name=txn.gateway_name,
                elapsed_since_create_s=elapsed,
                extra_data={'simulated': True, 'paid_at': txn.paid_at.isoformat()},
            )
            return True
        except QRISTransaction.DoesNotExist:
            logger.warning('QRIS_SIMULATE_NOT_FOUND txn_id=%s', transaction_id)
            _audit_log(
                event='error',
                txn_ref=transaction_id,
                error_message='Simulate failed — transaction not found or not pending',
            )
            return False


def get_payment_gateway() -> PaymentGateway:
    """Factory function to get the configured payment gateway."""
    gateway_type = getattr(settings, 'PAYMENT_GATEWAY', 'mock')

    if gateway_type == 'mock':
        return MockQRISGateway()
    # Future: add 'midtrans', 'xendit', etc.
    else:
        raise ValueError(f"Unknown payment gateway: {gateway_type}")
