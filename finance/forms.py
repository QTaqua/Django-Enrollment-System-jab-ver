"""Forms for the finance (Cashier/Administrator) screens."""

from django import forms

from accounts.forms import BootstrapFormMixin
from academics.models import Student
from finance.models import Adjustment, Payment, ScholarshipAward


class PaymentForm(BootstrapFormMixin, forms.Form):
    receipt_number = forms.CharField(max_length=40)
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    method = forms.ChoiceField(choices=Payment.Method.choices)
    reference_note = forms.CharField(max_length=120, required=False)


class AdjustmentForm(BootstrapFormMixin, forms.Form):
    adjustment_type = forms.ChoiceField(choices=Adjustment.Type.choices)
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    reason = forms.CharField(max_length=255)


class ReviseAssessmentForm(BootstrapFormMixin, forms.Form):
    reason = forms.CharField(max_length=255, label="Revision reason")


class ScholarshipForm(BootstrapFormMixin, forms.Form):
    student = forms.ModelChoiceField(
        queryset=Student.objects.select_related("user").order_by("student_number")
    )
    sponsor = forms.CharField(max_length=150)
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].label_from_instance = (
            lambda s: f"{s.student_number} - {s.user.get_full_name() or s.user.username}"
        )
