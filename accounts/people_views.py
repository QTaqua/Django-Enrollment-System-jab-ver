"""Registrar-managed student and instructor account screens.

Registrars may create and update accounts. Administrators receive read-only
list/detail access and cannot POST to create/update endpoints. The account
services own their transactions; ``IntegrityError`` is handled only after the
service has rolled back.
"""

import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.forms import (
    InstructorAccountForm,
    InstructorProfileForm,
    StudentAccountForm,
    StudentProfileForm,
)
from accounts.models import User
from accounts.permissions import RegistrarReadOnlyMixin, RegistrarRequiredMixin
from accounts.services import (
    CONFLICT_ERROR,
    create_instructor_account,
    create_student_account,
    update_instructor_profile,
    update_student_profile,
)
from academics.models import Instructor, Student

logger = logging.getLogger(__name__)


class PeopleListView(RegistrarReadOnlyMixin, ListView):
    template_name = "accounts/people/person_list.html"
    context_object_name = "objects"
    columns = ()
    create_url_name = None
    detail_url_name = None
    title = "People"
    entity_name = "Account"

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


class PeopleDetailView(RegistrarReadOnlyMixin, DetailView):
    template_name = "accounts/people/person_detail.html"
    context_object_name = "object"
    fields_display = ()
    update_url_name = None
    list_url_name = None
    title = "Account Details"

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


class StudentListView(PeopleListView):
    model = Student
    title = "Students"
    entity_name = "Student"
    columns = (
        ("Student No.", "student_number"),
        ("Name", "user.get_full_name"),
        ("Username", "user.username"),
        ("Curriculum", "curriculum"),
        ("Year Level", "year_level"),
    )
    create_url_name = "people:student_create"
    detail_url_name = "people:student_detail"


class StudentDetailView(PeopleDetailView):
    model = Student
    title = "Student Details"
    fields_display = (
        ("Student No.", "student_number"),
        ("Username", "user.username"),
        ("Full Name", "user.get_full_name"),
        ("Email", "user.email"),
        ("Phone", "user.phone"),
        ("Address", "user.address"),
        ("Curriculum", "curriculum"),
        ("Year Level", "year_level"),
    )
    update_url_name = "people:student_update"
    list_url_name = "people:student_list"


class InstructorListView(PeopleListView):
    model = Instructor
    title = "Instructors"
    entity_name = "Instructor"
    columns = (
        ("Employee No.", "employee_number"),
        ("Name", "user.get_full_name"),
        ("Username", "user.username"),
    )
    create_url_name = "people:instructor_create"
    detail_url_name = "people:instructor_detail"


class InstructorDetailView(PeopleDetailView):
    model = Instructor
    title = "Instructor Details"
    fields_display = (
        ("Employee No.", "employee_number"),
        ("Username", "user.username"),
        ("Full Name", "user.get_full_name"),
        ("Email", "user.email"),
        ("Phone", "user.phone"),
        ("Address", "user.address"),
    )
    update_url_name = "people:instructor_update"
    list_url_name = "people:instructor_list"


class _PeopleFormView(View):
    template_name = "accounts/people/person_form.html"
    title = "Account"

    def form_context(self, form):
        return {
            "form": form,
            "title": self.title,
            "cancel_url": reverse(self.list_url_name),
        }

    def render_form(self, request, form):
        return render(request, self.template_name, self.form_context(form))


class StudentCreateView(RegistrarRequiredMixin, _PeopleFormView):
    title = "Add Student Account"
    list_url_name = "people:student_list"

    def get(self, request):
        return self.render_form(request, StudentAccountForm())

    def post(self, request):
        form = StudentAccountForm(request.POST)
        if form.is_valid():
            try:
                student = create_student_account(
                    username=form.cleaned_data["username"],
                    password=form.cleaned_data["password1"],
                    student_number=form.cleaned_data["student_number"],
                    curriculum=form.cleaned_data["curriculum"],
                    year_level=form.cleaned_data["year_level"],
                    **form.user_fields(),
                )
            except IntegrityError:
                logger.warning(
                    "Integrity conflict creating student account in %s",
                    self.__class__.__name__,
                )
                form.add_error(None, CONFLICT_ERROR)
            except ValidationError as exc:
                form.add_error(None, exc.messages)
            else:
                messages.success(request, "Student account created successfully.")
                return redirect("people:student_detail", pk=student.pk)
        return self.render_form(request, form)


class StudentUpdateView(RegistrarRequiredMixin, _PeopleFormView):
    title = "Edit Student Account"
    list_url_name = "people:student_list"
    detail_url_name = "people:student_detail"

    def get_object(self, pk):
        return get_object_or_404(
            Student.objects.select_related("user", "curriculum"), pk=pk
        )

    def get(self, request, pk):
        student = self.get_object(pk)
        return self.render_form(request, StudentProfileForm(student=student))

    def post(self, request, pk):
        student = self.get_object(pk)
        form = StudentProfileForm(request.POST, student=student)
        if form.is_valid():
            try:
                student = update_student_profile(
                    student,
                    user_fields=form.user_fields(),
                    profile_fields=form.profile_fields(),
                    password=form.cleaned_data.get("password1") or None,
                )
            except IntegrityError:
                logger.warning(
                    "Integrity conflict updating student account in %s",
                    self.__class__.__name__,
                )
                form.add_error(None, CONFLICT_ERROR)
            except ValidationError as exc:
                form.add_error(None, exc.messages)
            else:
                messages.success(request, "Student account updated successfully.")
                return redirect("people:student_detail", pk=student.pk)
        return self.render_form(request, form)


class InstructorCreateView(RegistrarRequiredMixin, _PeopleFormView):
    title = "Add Instructor Account"
    list_url_name = "people:instructor_list"

    def get(self, request):
        return self.render_form(request, InstructorAccountForm())

    def post(self, request):
        form = InstructorAccountForm(request.POST)
        if form.is_valid():
            try:
                instructor = create_instructor_account(
                    username=form.cleaned_data["username"],
                    password=form.cleaned_data["password1"],
                    employee_number=form.cleaned_data["employee_number"],
                    **form.user_fields(),
                )
            except IntegrityError:
                logger.warning(
                    "Integrity conflict creating instructor account in %s",
                    self.__class__.__name__,
                )
                form.add_error(None, CONFLICT_ERROR)
            except ValidationError as exc:
                form.add_error(None, exc.messages)
            else:
                messages.success(request, "Instructor account created successfully.")
                return redirect("people:instructor_detail", pk=instructor.pk)
        return self.render_form(request, form)


class InstructorUpdateView(RegistrarRequiredMixin, _PeopleFormView):
    title = "Edit Instructor Account"
    list_url_name = "people:instructor_list"
    detail_url_name = "people:instructor_detail"

    def get_object(self, pk):
        return get_object_or_404(
            Instructor.objects.select_related("user"), pk=pk
        )

    def get(self, request, pk):
        instructor = self.get_object(pk)
        return self.render_form(
            request, InstructorProfileForm(instructor=instructor)
        )

    def post(self, request, pk):
        instructor = self.get_object(pk)
        form = InstructorProfileForm(request.POST, instructor=instructor)
        if form.is_valid():
            try:
                instructor = update_instructor_profile(
                    instructor,
                    user_fields=form.user_fields(),
                    profile_fields=form.profile_fields(),
                    password=form.cleaned_data.get("password1") or None,
                )
            except IntegrityError:
                logger.warning(
                    "Integrity conflict updating instructor account in %s",
                    self.__class__.__name__,
                )
                form.add_error(None, CONFLICT_ERROR)
            except ValidationError as exc:
                form.add_error(None, exc.messages)
            else:
                messages.success(request, "Instructor account updated successfully.")
                return redirect("people:instructor_detail", pk=instructor.pk)
        return self.render_form(request, form)
