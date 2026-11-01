"""Initialize version-1 snapshots and allocations for pre-existing finance data.

For each existing ``Assessment`` we create an immutable ``AssessmentVersion``
(v1) whose status/total mirror the current compatibility fields, plus a single
``AssessmentLine`` snapshot capturing the pre-itemization total (no fee rule).
``current_version`` is pointed at it. Every existing ``RECEIVED`` payment is
allocated in full to that version so balances are preserved exactly;
``CANCELLED`` (and any other non-received) payments are left unallocated, keeping
their existing meaning. A single ``FinancePolicy`` row is created with approved
defaults (previous-term balance = WARN).

No records are deleted or reinterpreted. Reverse removes only the rows this
migration created.
"""

from decimal import Decimal

from django.db import migrations


def forward(apps, schema_editor):
    Assessment = apps.get_model("finance", "Assessment")
    AssessmentVersion = apps.get_model("finance", "AssessmentVersion")
    AssessmentLine = apps.get_model("finance", "AssessmentLine")
    Payment = apps.get_model("finance", "Payment")
    PaymentAllocation = apps.get_model("finance", "PaymentAllocation")
    FinancePolicy = apps.get_model("finance", "FinancePolicy")

    FinancePolicy.objects.get_or_create(
        pk=1,
        defaults={
            "previous_term_balance": "WARN",
            "overpayment_becomes_credit": True,
            "credit_application_requires_approval": True,
            "refund_requires_approval": True,
        },
    )

    for assessment in Assessment.objects.all():
        if assessment.current_version_id is not None:
            continue
        version = AssessmentVersion.objects.create(
            assessment=assessment,
            version_number=1,
            status=assessment.status,  # DRAFT / FINALIZED preserved
            total_amount=assessment.total_amount,
            finalized_at=(
                assessment.assessed_at
                if assessment.status == "FINALIZED"
                else None
            ),
            revision_reason="",
        )
        AssessmentLine.objects.create(
            version=version,
            fee_category="OTHER",
            description="Migrated assessment total (pre-itemization)",
            quantity=None,
            unit_amount=assessment.total_amount,
            line_total=assessment.total_amount,
            fee_rule=None,
            fee_rule_name="",
            fee_rule_scope="",
        )
        assessment.current_version = version
        assessment.save(update_fields=["current_version"])

        received = Payment.objects.filter(
            assessment=assessment, status="RECEIVED"
        )
        for payment in received:
            already = PaymentAllocation.objects.filter(payment=payment).exists()
            if already:
                continue
            PaymentAllocation.objects.create(
                payment=payment,
                version=version,
                amount=payment.amount,
                created_at=payment.payment_date,
            )


def backward(apps, schema_editor):
    Assessment = apps.get_model("finance", "Assessment")
    AssessmentVersion = apps.get_model("finance", "AssessmentVersion")
    AssessmentLine = apps.get_model("finance", "AssessmentLine")
    PaymentAllocation = apps.get_model("finance", "PaymentAllocation")
    FinancePolicy = apps.get_model("finance", "FinancePolicy")

    Assessment.objects.update(current_version=None)
    PaymentAllocation.objects.all().delete()
    AssessmentLine.objects.all().delete()
    AssessmentVersion.objects.all().delete()
    FinancePolicy.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0002_finance_versioning_and_ledger"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
