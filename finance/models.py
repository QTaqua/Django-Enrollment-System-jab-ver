"""Finance data model (Milestone B).

Design goals (financial integrity):
* ``Assessment`` stays one-to-one with ``Enrollment`` (the enrollment-level
  parent). Per-assessment history lives in immutable ``AssessmentVersion`` +
  ``AssessmentLine`` snapshots; ``Assessment.current_version`` points at the one
  valid version that determines the current amount due. Historical versions are
  never summed together.
* Fees are computed from configurable ``FeeRule`` rows with category-aware
  stacking and COURSE > PROGRAM > GENERAL precedence within a category.
* ``Payment`` keeps its existing ``RECEIVED``/``CANCELLED`` meanings; ``PENDING``
  and ``REVERSED`` are added. Payments are linked to a version through explicit
  ``PaymentAllocation`` rows so money is traceable and never double-counted.
* Credits/refunds/reversals/corrections are explicit ``Adjustment`` rows with an
  approval trail (creator may not approve their own). Scholarships are separate
  ``ScholarshipAward`` records, never faked as cash. ``FinancePolicy`` holds the
  configurable business policy. ``FinanceAuditLog`` records finance actions.

All monetary math uses ``Decimal``. Balances are computed by the authoritative
service in ``finance.services`` (see ``assessment_balance``).
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class FeeCategory(models.TextChoices):
    TUITION = "TUITION", "Tuition"
    MISCELLANEOUS = "MISCELLANEOUS", "Miscellaneous"
    LABORATORY = "LABORATORY", "Laboratory"
    LIBRARY = "LIBRARY", "Library"
    REGISTRATION = "REGISTRATION", "Registration"
    OTHER = "OTHER", "Other"


class FeeRule(models.Model):
    """A configurable fee. Fees in different categories stack; within one
    category the most specific applicable scope wins (COURSE > PROGRAM > GENERAL).
    """

    class Scope(models.TextChoices):
        COURSE = "COURSE", "Course-specific"
        PROGRAM = "PROGRAM", "Program-specific"
        GENERAL = "GENERAL", "General"

    class Computation(models.TextChoices):
        PER_UNIT = "PER_UNIT", "Per unit"
        FIXED = "FIXED", "Fixed"

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=FeeCategory.choices)
    scope = models.CharField(max_length=20, choices=Scope.choices)
    course = models.ForeignKey(
        "academics.Course", null=True, blank=True,
        on_delete=models.PROTECT, db_column="course_id",
    )
    program = models.ForeignKey(
        "academics.Program", null=True, blank=True,
        on_delete=models.PROTECT, db_column="program_id",
    )
    computation = models.CharField(max_length=20, choices=Computation.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    year_level = models.IntegerField(null=True, blank=True)
    term = models.ForeignKey(
        "academics.AcademicTerm", null=True, blank=True,
        on_delete=models.PROTECT, db_column="term_id",
    )
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fee_rule"
        ordering = ["category", "scope", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="ck_fee_rule_amount_non_negative",
            ),
            models.CheckConstraint(
                condition=(
                    (models.Q(scope="COURSE") & models.Q(course__isnull=False)
                     & models.Q(program__isnull=True))
                    | (models.Q(scope="PROGRAM") & models.Q(program__isnull=False)
                       & models.Q(course__isnull=True))
                    | (models.Q(scope="GENERAL") & models.Q(course__isnull=True)
                       & models.Q(program__isnull=True))
                ),
                name="ck_fee_rule_scope_target",
            ),
        ]

    def __str__(self):
        return f"{self.get_category_display()} - {self.name} ({self.scope})"


class Assessment(models.Model):
    """The single assessment for an enrollment (enrollment-level parent).

    ``total_amount`` and ``status`` are compatibility/display mirrors of the
    current version. The authoritative amount and balance come from
    ``current_version`` and ``finance.services.assessment_balance``.
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
    current_version = models.ForeignKey(
        "finance.AssessmentVersion", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
        db_column="current_version_id",
    )
    needs_review = models.BooleanField(default=False)

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
        from finance.services import assessment_amount_paid
        return assessment_amount_paid(assessment=self)

    @property
    def balance(self):
        from finance.services import assessment_balance
        return assessment_balance(assessment=self)

    @property
    def is_finalized(self):
        return self.status == self.Status.FINALIZED

    def __str__(self):
        return f"Assessment #{self.pk} for enrollment #{self.enrollment_id}"


class AssessmentVersion(models.Model):
    """An immutable-once-finalized snapshot of an assessment's charges."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FINALIZED = "FINALIZED", "Finalized"
        SUPERSEDED = "SUPERSEDED", "Superseded"

    id = models.AutoField(primary_key=True)
    assessment = models.ForeignKey(
        Assessment, on_delete=models.PROTECT,
        related_name="versions", db_column="assessment_id",
    )
    version_number = models.IntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    created_at = models.DateTimeField(default=timezone.now)
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="+", db_column="created_by_id",
    )
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="+", db_column="finalized_by_id",
    )
    revision_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "assessment_version"
        ordering = ["assessment_id", "version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "version_number"],
                name="uq_assessment_version_number",
            ),
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=0),
                name="ck_assessment_version_total_non_negative",
            ),
        ]

    @property
    def is_finalized(self):
        return self.status == self.Status.FINALIZED

    def __str__(self):
        return f"Assessment #{self.assessment_id} v{self.version_number} ({self.status})"


class AssessmentLine(models.Model):
    """One itemized charge on an assessment version (immutable snapshot)."""

    id = models.AutoField(primary_key=True)
    version = models.ForeignKey(
        AssessmentVersion, on_delete=models.PROTECT,
        related_name="lines", db_column="version_id",
    )
    fee_category = models.CharField(max_length=20, choices=FeeCategory.choices)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    unit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    fee_rule = models.ForeignKey(
        FeeRule, null=True, blank=True,
        on_delete=models.PROTECT, db_column="fee_rule_id",
    )
    fee_rule_name = models.CharField(max_length=150, blank=True)
    fee_rule_scope = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "assessment_line"
        ordering = ["version_id", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(line_total__gte=0),
                name="ck_assessment_line_total_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.fee_category}: {self.description} = {self.line_total}"


class Payment(models.Model):
    """A payment recorded against one assessment.

    ``RECEIVED`` keeps its existing meaning (a confirmed, received payment that
    counts toward the balance via its allocations). ``PENDING``/``CANCELLED``/
    ``REVERSED`` never count. Scholarships are NOT payments (see ScholarshipAward).
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RECEIVED = "RECEIVED", "Received"
        CANCELLED = "CANCELLED", "Cancelled"
        REVERSED = "REVERSED", "Reversed"

    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        CHECK = "CHECK", "Check"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank transfer"
        ONLINE = "ONLINE", "Online payment"
        E_WALLET = "E_WALLET", "E-wallet"

    id = models.AutoField(primary_key=True)
    assessment = models.ForeignKey(
        Assessment, on_delete=models.PROTECT,
        related_name="payments", db_column="assessment_id",
    )
    received_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT,
        related_name="payments_received", db_column="received_by_id",
    )
    receipt_number = models.CharField(max_length=40)
    payment_date = models.DateTimeField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RECEIVED
    )
    reference_note = models.CharField(max_length=120, blank=True)
    reversed_at = models.DateTimeField(null=True, blank=True)

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

    @property
    def allocated_amount(self):
        from django.db.models import Sum
        total = self.allocations.aggregate(total=Sum("amount"))["total"]
        return total if total is not None else Decimal("0.00")

    @property
    def unallocated_amount(self):
        return self.amount - self.allocated_amount

    @property
    def counts_toward_balance(self):
        return self.status == self.Status.RECEIVED

    def __str__(self):
        return f"{self.receipt_number} - {self.amount} ({self.status})"


class PaymentAllocation(models.Model):
    """Explicit link of a payment to the assessment version it was applied to."""

    id = models.AutoField(primary_key=True)
    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT,
        related_name="allocations", db_column="payment_id",
    )
    version = models.ForeignKey(
        AssessmentVersion, on_delete=models.PROTECT,
        related_name="allocations", db_column="version_id",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="+", db_column="created_by_id",
    )

    class Meta:
        db_table = "payment_allocation"
        ordering = ["payment_id", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="ck_payment_allocation_amount_positive",
            ),
        ]

    def __str__(self):
        return f"Payment #{self.payment_id} -> version #{self.version_id}: {self.amount}"


class Adjustment(models.Model):
    """An auditable credit/refund/reversal/correction with an approval trail."""

    class Type(models.TextChoices):
        CREDIT = "CREDIT", "Credit"
        REFUND = "REFUND", "Refund"
        REVERSAL = "REVERSAL", "Reversal"
        CORRECTION = "CORRECTION", "Correction"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    id = models.AutoField(primary_key=True)
    adjustment_type = models.CharField(max_length=20, choices=Type.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255)
    assessment = models.ForeignKey(
        Assessment, null=True, blank=True, on_delete=models.PROTECT,
        related_name="adjustments", db_column="assessment_id",
    )
    version = models.ForeignKey(
        AssessmentVersion, null=True, blank=True, on_delete=models.PROTECT,
        related_name="adjustments", db_column="version_id",
    )
    payment = models.ForeignKey(
        Payment, null=True, blank=True, on_delete=models.PROTECT,
        related_name="adjustments", db_column="payment_id",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="adjustments_created",
        db_column="created_by_id",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="adjustments_approved",
        db_column="approved_by_id",
    )
    created_at = models.DateTimeField(default=timezone.now)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "adjustment"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="ck_adjustment_amount_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(approved_by__isnull=True)
                    | ~models.Q(approved_by=models.F("created_by"))
                ),
                name="ck_adjustment_approver_not_creator",
            ),
        ]

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    def __str__(self):
        return f"{self.adjustment_type} {self.amount} ({self.status})"


class ScholarshipAward(models.Model):
    """Financial aid, kept distinct from cash/electronic payments."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        APPLIED = "APPLIED", "Applied"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(
        "academics.Student", on_delete=models.PROTECT,
        related_name="scholarships", db_column="student_id",
    )
    sponsor = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    assessment = models.ForeignKey(
        Assessment, null=True, blank=True, on_delete=models.PROTECT,
        related_name="scholarships", db_column="assessment_id",
    )
    version = models.ForeignKey(
        AssessmentVersion, null=True, blank=True, on_delete=models.PROTECT,
        related_name="scholarships", db_column="version_id",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="scholarships_created",
        db_column="created_by_id",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="scholarships_approved",
        db_column="approved_by_id",
    )
    created_at = models.DateTimeField(default=timezone.now)
    approved_at = models.DateTimeField(null=True, blank=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        db_table = "scholarship_award"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="ck_scholarship_amount_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(approved_by__isnull=True)
                    | ~models.Q(approved_by=models.F("created_by"))
                ),
                name="ck_scholarship_approver_not_creator",
            ),
        ]

    @property
    def counts_toward_balance(self):
        return self.status in (self.Status.APPROVED, self.Status.APPLIED)

    def __str__(self):
        return f"{self.sponsor} scholarship {self.amount} ({self.status})"


class FinancePolicy(models.Model):
    """Single-row configurable finance policy. Load via ``FinancePolicy.load()``."""

    class PreviousBalance(models.TextChoices):
        WARN = "WARN", "Warn only"
        BLOCK = "BLOCK", "Block enrollment"
        OFF = "OFF", "No restriction"

    id = models.AutoField(primary_key=True)
    previous_term_balance = models.CharField(
        max_length=10, choices=PreviousBalance.choices,
        default=PreviousBalance.WARN,
    )
    overpayment_becomes_credit = models.BooleanField(default=True)
    credit_application_requires_approval = models.BooleanField(default=True)
    refund_requires_approval = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "finance_policy"

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Finance policy"


class Reconciliation(models.Model):
    """Authorized reconciliation record of collected funds vs verified records.

    Milestone B provides the data structure and a basic compute service; a full
    investigative UI/workflow is a later enhancement (documented limitation).
    """

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        RESOLVED = "RESOLVED", "Resolved"

    id = models.AutoField(primary_key=True)
    term = models.ForeignKey(
        "academics.AcademicTerm", null=True, blank=True,
        on_delete=models.PROTECT, db_column="term_id",
    )
    method = models.CharField(max_length=20, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    recorded_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    verified_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    discrepancy = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="+", db_column="performed_by_id",
    )
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "reconciliation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reconciliation #{self.pk} ({self.method or 'ALL'}) {self.status}"


class FinanceAuditLog(models.Model):
    """Append-only audit trail for finance actions."""

    id = models.AutoField(primary_key=True)
    # Append-only log: the event is preserved even if the actor is later
    # removed, so actor is nulled (never blocks user deletion).
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", db_column="actor_id",
    )
    action = models.CharField(max_length=60)
    detail = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "finance_audit_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action}"
