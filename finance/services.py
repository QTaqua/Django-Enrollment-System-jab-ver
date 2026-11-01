"""Minimal finance helpers for the simplified enrollment system.

The balance is always derived from the assessment total and the ``RECEIVED``
payments recorded against it.  There are no fee rules, assessment lines or
payment allocations in this design.
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from .models import Payment


def _as_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("Amount must be a valid decimal number.")


def assessment_balance(*, assessment):
    """Return ``total_amount`` minus all RECEIVED payments."""
    paid = (
        Payment.objects.filter(
            assessment=assessment, status=Payment.Status.RECEIVED
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    return assessment.total_amount - paid


@transaction.atomic
def record_payment(
    *,
    assessment,
    received_by,
    receipt_number,
    amount,
    method,
    status=Payment.Status.RECEIVED,
):
    """Record one payment against an assessment."""
    amount = _as_decimal(amount)
    if amount <= 0:
        raise ValidationError("Payment amount must be greater than zero.")

    return Payment.objects.create(
        assessment=assessment,
        received_by=received_by,
        receipt_number=receipt_number,
        amount=amount,
        method=method,
        status=status,
    )
