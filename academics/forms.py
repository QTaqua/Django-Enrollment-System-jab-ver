"""ModelForms for Registrar-managed academic master data."""

from django import forms
from django.core.exceptions import ValidationError

from accounts.forms import BootstrapFormMixin
from academics.models import (
    AcademicTerm,
    College,
    Course,
    CoursePrerequisite,
    Curriculum,
    CurriculumCourse,
    Program,
)


class CollegeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = College
        fields = ["college_code", "name", "is_active"]


class ProgramForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Program
        fields = ["college", "program_code", "name", "description", "is_active"]


class CurriculumForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Curriculum
        fields = ["program", "curriculum_code", "effective_year", "is_active"]

    def clean_effective_year(self):
        effective_year = self.cleaned_data["effective_year"]
        if effective_year < 1:
            raise ValidationError("Effective year must be 1 or greater.")
        return effective_year


class CourseForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Course
        fields = ["course_code", "title", "description", "units", "is_active"]

    def clean_units(self):
        units = self.cleaned_data["units"]
        if units <= 0:
            raise ValidationError("Units must be greater than zero.")
        return units


class CurriculumCourseForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CurriculumCourse
        fields = [
            "curriculum",
            "course",
            "year_level",
            "recommended_semester",
            "course_category",
        ]

    def clean_year_level(self):
        year_level = self.cleaned_data["year_level"]
        if year_level < 1:
            raise ValidationError("Year level must be 1 or greater.")
        return year_level

    def clean_recommended_semester(self):
        semester = self.cleaned_data["recommended_semester"]
        if semester < 1:
            raise ValidationError("Recommended semester must be 1 or greater.")
        return semester


class CoursePrerequisiteForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CoursePrerequisite
        fields = ["course", "prerequisite_course"]

    def clean(self):
        cleaned = super().clean()
        course = cleaned.get("course")
        prerequisite = cleaned.get("prerequisite_course")
        if course and prerequisite and course.pk == prerequisite.pk:
            self.add_error(
                "prerequisite_course",
                "A course cannot be its own prerequisite.",
            )
        return cleaned


class AcademicTermForm(BootstrapFormMixin, forms.ModelForm):
    """Academic year intentionally remains a free-form CharField.

    The model stores ``academic_year`` as ``CharField(max_length=9)`` and the
    database enforces only length/uniqueness. No ``YYYY-YYYY`` format regex is
    added here so form validation matches the frozen schema.
    """

    class Meta:
        model = AcademicTerm
        fields = [
            "academic_year",
            "semester_number",
            "start_date",
            "end_date",
            "enrollment_open",
        ]

    def clean_semester_number(self):
        semester_number = self.cleaned_data["semester_number"]
        if semester_number < 1:
            raise ValidationError("Semester number must be 1 or greater.")
        return semester_number

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date must be on or after the start date.")
        return cleaned
