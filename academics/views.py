"""Registrar academic master-data screens.

Registrars may create and update records. Administrators receive read-only
list/detail access. Integrity conflicts are caught only after the atomic
block that performed the write has rolled back.
"""

import logging

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from academics.forms import (
    AcademicTermForm,
    CollegeForm,
    CourseForm,
    CoursePrerequisiteForm,
    CurriculumCourseForm,
    CurriculumForm,
    ProgramForm,
)
from academics.models import (
    AcademicTerm,
    College,
    Course,
    CoursePrerequisite,
    Curriculum,
    CurriculumCourse,
    Program,
)
from accounts.models import User
from accounts.permissions import RegistrarReadOnlyMixin, RegistrarRequiredMixin
from accounts.services import CONFLICT_ERROR

logger = logging.getLogger(__name__)


class AcademicListView(RegistrarReadOnlyMixin, ListView):
    template_name = "academics/master_list.html"
    context_object_name = "objects"
    columns = ()
    create_url_name = None
    detail_url_name = None
    title = "Academic Data"
    entity_name = "Record"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "title": self.title,
                "entity_name": self.entity_name,
                "columns": self.columns,
                "create_url_name": self.create_url_name,
                "detail_url_name": self.detail_url_name,
                "can_create": getattr(self.request.user, "role", None)
                == User.Role.REGISTRAR,
            }
        )
        return context


class AcademicDetailView(RegistrarReadOnlyMixin, DetailView):
    template_name = "academics/master_detail.html"
    context_object_name = "object"
    fields_display = ()
    update_url_name = None
    list_url_name = None
    title = "Academic Record"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "title": self.title,
                "fields": self.fields_display,
                "update_url_name": self.update_url_name,
                "list_url_name": self.list_url_name,
                "can_edit": getattr(self.request.user, "role", None)
                == User.Role.REGISTRAR,
            }
        )
        return context


class AcademicCreateView(RegistrarRequiredMixin, CreateView):
    template_name = "academics/master_form.html"
    detail_url_name = None
    list_url_name = None
    title = "Add Record"

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save()
        except IntegrityError:
            logger.warning(
                "Integrity conflict creating %s in %s",
                self.model.__name__,
                self.__class__.__name__,
            )
            form.add_error(None, CONFLICT_ERROR)
            return self.form_invalid(form)
        messages.success(
            self.request,
            f"{self.model._meta.verbose_name.title()} created successfully.",
        )
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(self.detail_url_name, args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "title": self.title,
                "submit_label": "Create",
                "cancel_url": reverse(self.list_url_name),
            }
        )
        return context


class AcademicUpdateView(RegistrarRequiredMixin, UpdateView):
    template_name = "academics/master_form.html"
    detail_url_name = None
    list_url_name = None
    title = "Edit Record"

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save()
        except IntegrityError:
            logger.warning(
                "Integrity conflict updating %s in %s",
                self.model.__name__,
                self.__class__.__name__,
            )
            form.add_error(None, CONFLICT_ERROR)
            return self.form_invalid(form)
        messages.success(
            self.request,
            f"{self.model._meta.verbose_name.title()} updated successfully.",
        )
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(self.detail_url_name, args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "title": self.title,
                "submit_label": "Save changes",
                "cancel_url": reverse(self.list_url_name),
            }
        )
        return context


# College
class CollegeListView(AcademicListView):
    model = College
    title = "Colleges"
    entity_name = "College"
    columns = (("Code", "college_code"), ("Name", "name"), ("Active", "is_active"))
    create_url_name = "academics:college_create"
    detail_url_name = "academics:college_detail"


class CollegeDetailView(AcademicDetailView):
    model = College
    title = "College Details"
    fields_display = (
        ("Code", "college_code"),
        ("Name", "name"),
        ("Active", "is_active"),
    )
    update_url_name = "academics:college_update"
    list_url_name = "academics:college_list"


class CollegeCreateView(AcademicCreateView):
    model = College
    form_class = CollegeForm
    title = "Add College"
    detail_url_name = "academics:college_detail"
    list_url_name = "academics:college_list"


class CollegeUpdateView(AcademicUpdateView):
    model = College
    form_class = CollegeForm
    title = "Edit College"
    detail_url_name = "academics:college_detail"
    list_url_name = "academics:college_list"


# Program
class ProgramListView(AcademicListView):
    model = Program
    title = "Programs"
    entity_name = "Program"
    columns = (
        ("Code", "program_code"),
        ("Name", "name"),
        ("College", "college"),
        ("Active", "is_active"),
    )
    create_url_name = "academics:program_create"
    detail_url_name = "academics:program_detail"


class ProgramDetailView(AcademicDetailView):
    model = Program
    title = "Program Details"
    fields_display = (
        ("Code", "program_code"),
        ("Name", "name"),
        ("College", "college"),
        ("Description", "description"),
        ("Active", "is_active"),
    )
    update_url_name = "academics:program_update"
    list_url_name = "academics:program_list"


class ProgramCreateView(AcademicCreateView):
    model = Program
    form_class = ProgramForm
    title = "Add Program"
    detail_url_name = "academics:program_detail"
    list_url_name = "academics:program_list"


class ProgramUpdateView(AcademicUpdateView):
    model = Program
    form_class = ProgramForm
    title = "Edit Program"
    detail_url_name = "academics:program_detail"
    list_url_name = "academics:program_list"


# Curriculum
class CurriculumListView(AcademicListView):
    model = Curriculum
    title = "Curricula"
    entity_name = "Curriculum"
    columns = (
        ("Code", "curriculum_code"),
        ("Program", "program"),
        ("Effective Year", "effective_year"),
        ("Active", "is_active"),
    )
    create_url_name = "academics:curriculum_create"
    detail_url_name = "academics:curriculum_detail"


class CurriculumDetailView(AcademicDetailView):
    model = Curriculum
    title = "Curriculum Details"
    fields_display = (
        ("Code", "curriculum_code"),
        ("Program", "program"),
        ("Effective Year", "effective_year"),
        ("Active", "is_active"),
    )
    update_url_name = "academics:curriculum_update"
    list_url_name = "academics:curriculum_list"


class CurriculumCreateView(AcademicCreateView):
    model = Curriculum
    form_class = CurriculumForm
    title = "Add Curriculum"
    detail_url_name = "academics:curriculum_detail"
    list_url_name = "academics:curriculum_list"


class CurriculumUpdateView(AcademicUpdateView):
    model = Curriculum
    form_class = CurriculumForm
    title = "Edit Curriculum"
    detail_url_name = "academics:curriculum_detail"
    list_url_name = "academics:curriculum_list"


# Course
class CourseListView(AcademicListView):
    model = Course
    title = "Courses"
    entity_name = "Course"
    columns = (
        ("Code", "course_code"),
        ("Title", "title"),
        ("Units", "units"),
        ("Active", "is_active"),
    )
    create_url_name = "academics:course_create"
    detail_url_name = "academics:course_detail"


class CourseDetailView(AcademicDetailView):
    model = Course
    title = "Course Details"
    fields_display = (
        ("Code", "course_code"),
        ("Title", "title"),
        ("Description", "description"),
        ("Units", "units"),
        ("Active", "is_active"),
    )
    update_url_name = "academics:course_update"
    list_url_name = "academics:course_list"


class CourseCreateView(AcademicCreateView):
    model = Course
    form_class = CourseForm
    title = "Add Course"
    detail_url_name = "academics:course_detail"
    list_url_name = "academics:course_list"


class CourseUpdateView(AcademicUpdateView):
    model = Course
    form_class = CourseForm
    title = "Edit Course"
    detail_url_name = "academics:course_detail"
    list_url_name = "academics:course_list"


# CurriculumCourse
class CurriculumCourseListView(AcademicListView):
    model = CurriculumCourse
    title = "Curriculum Courses"
    entity_name = "Curriculum Course"
    columns = (
        ("Curriculum", "curriculum"),
        ("Course", "course"),
        ("Year Level", "year_level"),
        ("Semester", "recommended_semester"),
        ("Category", "course_category"),
    )
    create_url_name = "academics:curriculum_course_create"
    detail_url_name = "academics:curriculum_course_detail"


class CurriculumCourseDetailView(AcademicDetailView):
    model = CurriculumCourse
    title = "Curriculum Course Details"
    fields_display = (
        ("Curriculum", "curriculum"),
        ("Course", "course"),
        ("Year Level", "year_level"),
        ("Recommended Semester", "recommended_semester"),
        ("Category", "course_category"),
    )
    update_url_name = "academics:curriculum_course_update"
    list_url_name = "academics:curriculum_course_list"


class CurriculumCourseCreateView(AcademicCreateView):
    model = CurriculumCourse
    form_class = CurriculumCourseForm
    title = "Add Curriculum Course"
    detail_url_name = "academics:curriculum_course_detail"
    list_url_name = "academics:curriculum_course_list"


class CurriculumCourseUpdateView(AcademicUpdateView):
    model = CurriculumCourse
    form_class = CurriculumCourseForm
    title = "Edit Curriculum Course"
    detail_url_name = "academics:curriculum_course_detail"
    list_url_name = "academics:curriculum_course_list"


# CoursePrerequisite
class CoursePrerequisiteListView(AcademicListView):
    model = CoursePrerequisite
    title = "Course Prerequisites"
    entity_name = "Course Prerequisite"
    columns = (
        ("Course", "course"),
        ("Prerequisite", "prerequisite_course"),
    )
    create_url_name = "academics:course_prerequisite_create"
    detail_url_name = "academics:course_prerequisite_detail"


class CoursePrerequisiteDetailView(AcademicDetailView):
    model = CoursePrerequisite
    title = "Course Prerequisite Details"
    fields_display = (
        ("Course", "course"),
        ("Prerequisite", "prerequisite_course"),
    )
    update_url_name = "academics:course_prerequisite_update"
    list_url_name = "academics:course_prerequisite_list"


class CoursePrerequisiteCreateView(AcademicCreateView):
    model = CoursePrerequisite
    form_class = CoursePrerequisiteForm
    title = "Add Course Prerequisite"
    detail_url_name = "academics:course_prerequisite_detail"
    list_url_name = "academics:course_prerequisite_list"


class CoursePrerequisiteUpdateView(AcademicUpdateView):
    model = CoursePrerequisite
    form_class = CoursePrerequisiteForm
    title = "Edit Course Prerequisite"
    detail_url_name = "academics:course_prerequisite_detail"
    list_url_name = "academics:course_prerequisite_list"


# AcademicTerm
class AcademicTermListView(AcademicListView):
    model = AcademicTerm
    title = "Academic Terms"
    entity_name = "Academic Term"
    columns = (
        ("Academic Year", "academic_year"),
        ("Semester", "semester_number"),
        ("Start", "start_date"),
        ("End", "end_date"),
        ("Enrollment Open", "enrollment_open"),
    )
    create_url_name = "academics:academic_term_create"
    detail_url_name = "academics:academic_term_detail"


class AcademicTermDetailView(AcademicDetailView):
    model = AcademicTerm
    title = "Academic Term Details"
    fields_display = (
        ("Academic Year", "academic_year"),
        ("Semester", "semester_number"),
        ("Start Date", "start_date"),
        ("End Date", "end_date"),
        ("Enrollment Open", "enrollment_open"),
    )
    update_url_name = "academics:academic_term_update"
    list_url_name = "academics:academic_term_list"


class AcademicTermCreateView(AcademicCreateView):
    model = AcademicTerm
    form_class = AcademicTermForm
    title = "Add Academic Term"
    detail_url_name = "academics:academic_term_detail"
    list_url_name = "academics:academic_term_list"


class AcademicTermUpdateView(AcademicUpdateView):
    model = AcademicTerm
    form_class = AcademicTermForm
    title = "Edit Academic Term"
    detail_url_name = "academics:academic_term_detail"
    list_url_name = "academics:academic_term_list"
