"""Forms for Registrar-managed enrollments."""

from django import forms

from accounts.forms import BootstrapFormMixin
from academics.models import AcademicTerm, Student
from scheduling.models import Section


def _section_label(section):
    if (
        section.day_of_week is not None
        and section.start_time is not None
        and section.end_time is not None
    ):
        schedule = (
            f"{section.get_day_of_week_display()} "
            f"{section.start_time.strftime('%H:%M')}-"
            f"{section.end_time.strftime('%H:%M')}"
        )
    else:
        schedule = "TBA"
    instructor = "Unassigned"
    if section.instructor is not None:
        instructor = (
            section.instructor.user.get_full_name()
            or section.instructor.user.username
        )
    return (
        f"{section.course.course_code} - {section.course.title} "
        f"[{section.section_code}] {schedule} / {instructor} "
        f"({section.get_status_display()})"
    )


class EnrollmentCreateForm(BootstrapFormMixin, forms.Form):
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        label="Student",
    )
    term = forms.ModelChoiceField(
        queryset=AcademicTerm.objects.none(),
        label="Academic term",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = (
            Student.objects.filter(user__is_active=True)
            .select_related("user", "curriculum")
            .order_by("student_number")
        )
        self.fields["student"].label_from_instance = lambda student: (
            f"{student.student_number} - "
            f"{student.user.get_full_name() or student.user.username}"
        )
        self.fields["term"].queryset = AcademicTerm.objects.order_by(
            "-academic_year", "semester_number"
        )


class AddSectionForm(BootstrapFormMixin, forms.Form):
    section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        label="Section",
    )

    def __init__(self, *args, term=None, **kwargs):
        super().__init__(*args, **kwargs)
        if term is not None:
            self.fields["section"].queryset = (
                Section.objects.filter(term=term)
                .select_related("course", "instructor__user", "term")
                .order_by("course__course_code", "section_code")
            )
        self.fields["section"].label_from_instance = _section_label
