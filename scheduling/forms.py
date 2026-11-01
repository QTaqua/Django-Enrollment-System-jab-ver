"""Forms for Registrar-managed class sections."""

from django import forms
from django.core.exceptions import ValidationError

from accounts.forms import BootstrapFormMixin
from accounts.models import User
from academics.models import AcademicTerm, Course, Instructor
from scheduling.models import Room, Section


class SectionForm(BootstrapFormMixin, forms.ModelForm):
    """Section create/update form.

    A section schedule is either completely TBA (day, start, and end are all
    blank) or completely specified. Partial schedules are never accepted.
    """

    class Meta:
        model = Section
        fields = [
            "course",
            "term",
            "instructor",
            "section_code",
            "capacity",
            "room",
            "room_code",
            "day_of_week",
            "start_time",
            "end_time",
            "status",
        ]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.order_by("course_code")
        self.fields["term"].queryset = AcademicTerm.objects.order_by(
            "-academic_year", "semester_number"
        )
        self.fields["instructor"].queryset = (
            Instructor.objects.select_related("user").order_by(
                "user__last_name", "user__first_name", "employee_number"
            )
        )
        self.fields["instructor"].label_from_instance = (
            lambda instructor: (
                f"{instructor.employee_number} - "
                f"{instructor.user.get_full_name() or instructor.user.username}"
            )
        )
        self.fields["room"].queryset = Room.objects.filter(
            is_active=True
        ).order_by("room_code")
        self.fields["room"].required = False
        self.fields["room"].label_from_instance = (
            lambda room: f"{room.room_code} - {room.name}" if room.name else room.room_code
        )
        self.fields["day_of_week"].required = False
        self.fields["start_time"].required = False
        self.fields["end_time"].required = False

    def clean_capacity(self):
        capacity = self.cleaned_data["capacity"]
        if capacity < 1:
            raise ValidationError("Capacity must be at least 1.")
        return capacity

    def clean(self):
        cleaned = super().clean()
        day = cleaned.get("day_of_week")
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")

        supplied = [value is not None for value in (day, start, end)]
        if any(supplied) and not all(supplied):
            self.add_error(
                "day_of_week",
                "Day, start time, and end time must all be provided together, "
                "or all left blank for a TBA section.",
            )
        elif all(supplied) and end <= start:
            self.add_error(
                "end_time", "End time must be later than start time."
            )

        instructor = cleaned.get("instructor")
        if instructor is not None:
            if not instructor.user.is_active:
                self.add_error(
                    "instructor", "The selected instructor account is inactive."
                )
            elif instructor.user.role != User.Role.INSTRUCTOR:
                self.add_error(
                    "instructor",
                    "The selected account is not an instructor profile.",
                )

        course = cleaned.get("course")
        term = cleaned.get("term")
        section_code = cleaned.get("section_code")
        if course and term and section_code:
            duplicates = Section.objects.filter(
                course=course, term=term, section_code=section_code
            )
            if self.instance.pk is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error(
                    "section_code",
                    "A section with this code already exists for this course "
                    "and academic term.",
                )

        return cleaned
