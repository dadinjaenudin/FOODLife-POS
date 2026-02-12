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
import uuid


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
            return QRISStatusResult(
                status='failed',
                transaction_id=transaction_id,
                error_message='Transaction not found',
            )

        # Check if expired
        if txn.status == 'pending' and txn.expires_at and timezone.now() > txn.expires_at:
            txn.status = 'expired'
            txn.save(update_fields=['status'])

        return QRISStatusResult(
            status=txn.status,
            transaction_id=txn.transaction_id,
            paid_at=txn.paid_at,
        )

    def cancel_transaction(self, transaction_id: str) -> bool:
        from .models import QRISTransaction

        try:
            txn = QRISTransaction.objects.get(transaction_id=transaction_id, status='pending')
            txn.status = 'cancelled'
            txn.save(update_fields=['status'])
            return True
        except QRISTransaction.DoesNotExist:
            return False

    def simulate_payment(self, transaction_id: str) -> bool:
        """DEV ONLY: Simulate a successful QRIS payment."""
        from .models import QRISTransaction

        try:
            txn = QRISTransaction.objects.get(transaction_id=transaction_id, status='pending')
            txn.status = 'paid'
            txn.paid_at = timezone.now()
            txn.gateway_response = {'simulated': True, 'paid_at': str(timezone.now())}
            txn.save(update_fields=['status', 'paid_at', 'gateway_response'])
            return True
        except QRISTransaction.DoesNotExist:
            return False


def get_payment_gateway() -> PaymentGateway:
    """Factory function to get the configured payment gateway."""
    gateway_type = getattr(settings, 'PAYMENT_GATEWAY', 'mock')

    if gateway_type == 'mock':
        return MockQRISGateway()
    # Future: add 'midtrans', 'xendit', etc.
    else:
        raise ValueError(f"Unknown payment gateway: {gateway_type}")
