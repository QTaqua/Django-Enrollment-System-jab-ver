from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Assessment(models.Model):
    """The single assessment for an enrollment.

    The balance is always derived from ``total_amount`` minus the payments
    recorded against this assessment; it is never stored as a column.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FINALIZED = "FINALIZED", "Finalized"

    id = models.AutoField(primary_key=True)
    enrollment = models.OneToOneField(
        "enrollment.Enrollment",
        on_delete=models.PROTECT,
        related_name="assessment",
        db_column="enrollment_id",
    )
    assessed_at = models.DateTimeField(default=timezone.now)
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "assessment"
        ordering = ["-assessed_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=0),
                name="ck_assessment_total_non_negative",
            ),
        ]

    @property
    def amount_paid(self):
        total = self.payments.filter(status=Payment.Status.RECEIVED).aggregate(
            total=Sum("amount")
        )["total"]
        return total if total is not None else Decimal("0.00")

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    @property
    def is_finalized(self):
        return self.status == self.Status.FINALIZED

    def __str__(self):
        return f"Assessment #{self.pk} for enrollment #{self.enrollment_id}"


class Payment(models.Model):
    """A payment recorded against one assessment.

    Only ``RECEIVED`` payments count toward the assessment balance.
    """

    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        CANCELLED = "CANCELLED", "Cancelled"

    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        CHECK = "CHECK", "Check"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank transfer"
        ONLINE = "ONLINE", "Online payment"

    id = models.AutoField(primary_key=True)
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.PROTECT,
        related_name="payments",
        db_column="assessment_id",
    )
    received_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="payments_received",
        db_column="received_by_id",
    )
    receipt_number = models.CharField(max_length=40)
    payment_date = models.DateTimeField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RECEIVED
    )

    class Meta:
        db_table = "payment"
        ordering = ["-payment_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["receipt_number"], name="uq_payment_receipt_number"
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="ck_payment_amount_positive",
            ),
        ]

    def __str__(self):
        return f"{self.receipt_number} - {self.amount} ({self.status})"
