"""Registrar section management screens.

Registrars create and update sections. Administrators receive read-only
list/detail access. Business rules live in ``scheduling.services``; the views
only map cleaned form data to service arguments and translate expected errors
into readable form errors.
"""

import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.models import User
from accounts.permissions import RegistrarReadOnlyMixin, RegistrarRequiredMixin
from accounts.services import CONFLICT_ERROR
from enrollment.models import Enrollment, EnrollmentDetail
from scheduling.forms import SectionForm
from scheduling.models import Section
from scheduling.services import create_section, update_section

logger = logging.getLogger(__name__)


def _enrolled_count_filter():
    return Q(enrollment_details__status=EnrollmentDetail.Status.ENROLLED) & ~Q(
        enrollment_details__enrollment__status=Enrollment.Status.CANCELLED
    )


class SectionListView(RegistrarReadOnlyMixin, ListView):
    model = Section
    template_name = "scheduling/section_list.html"
    context_object_name = "sections"

    def get_queryset(self):
        return (
            Section.objects.select_related(
                "course", "term", "instructor__user"
            )
            .annotate(
                enrolled_count=Count(
                    "enrollment_details",
                    filter=_enrolled_count_filter(),
                    distinct=True,
                )
            )
            .order_by("-term__academic_year", "term__semester_number", "course__course_code", "section_code")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage"] = (
            getattr(self.request.user, "role", None) == User.Role.REGISTRAR
        )
        return context


class SectionDetailView(RegistrarReadOnlyMixin, DetailView):
    model = Section
    template_name = "scheduling/section_detail.html"
    context_object_name = "section"

    def get_queryset(self):
        return Section.objects.select_related(
            "course", "term", "instructor__user"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        section = self.object
        enrolled_details = (
            EnrollmentDetail.objects.filter(
                section=section,
                status=EnrollmentDetail.Status.ENROLLED,
            )
            .exclude(enrollment__status=Enrollment.Status.CANCELLED)
            .select_related("enrollment__student__user")
            .order_by("enrollment__student__student_number")
        )
        context.update(
            {
                "enrolled_details": enrolled_details,
                "enrolled_count": enrolled_details.count(),
                "can_manage": getattr(self.request.user, "role", None)
                == User.Role.REGISTRAR,
            }
        )
        return context


class SectionCreateView(RegistrarRequiredMixin, CreateView):
    model = Section
    form_class = SectionForm
    template_name = "scheduling/section_form.html"

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            self.object = create_section(
                course=data["course"],
                term=data["term"],
                section_code=data["section_code"],
                capacity=data["capacity"],
                instructor=data["instructor"],
                room=data["room"],
                room_code=data["room_code"],
                day_of_week=data["day_of_week"],
                start_time=data["start_time"],
                end_time=data["end_time"],
                status=data["status"],
            )
        except ValidationError as exc:
            form.add_error(None, exc.messages)
            return self.form_invalid(form)
        except IntegrityError:
            logger.warning(
                "Integrity conflict creating section in %s",
                self.__class__.__name__,
            )
            form.add_error(None, CONFLICT_ERROR)
            return self.form_invalid(form)
        messages.success(self.request, "Section created successfully.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("scheduling:section_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "title": "Add Section",
                "submit_label": "Create",
                "cancel_url": reverse("scheduling:section_list"),
            }
        )
        return context


class SectionUpdateView(RegistrarRequiredMixin, UpdateView):
    model = Section
    form_class = SectionForm
    template_name = "scheduling/section_form.html"

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            self.object = update_section(
                self.object,
                course=data["course"],
                term=data["term"],
                section_code=data["section_code"],
                capacity=data["capacity"],
                instructor=data["instructor"],
                room=data["room"],
                room_code=data["room_code"],
                day_of_week=data["day_of_week"],
                start_time=data["start_time"],
                end_time=data["end_time"],
                status=data["status"],
            )
        except ValidationError as exc:
            form.add_error(None, exc.messages)
            return self.form_invalid(form)
        except IntegrityError:
            logger.warning(
                "Integrity conflict updating section in %s",
                self.__class__.__name__,
            )
            form.add_error(None, CONFLICT_ERROR)
            return self.form_invalid(form)
        messages.success(self.request, "Section updated successfully.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("scheduling:section_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "title": "Edit Section",
                "submit_label": "Save changes",
                "cancel_url": reverse(
                    "scheduling:section_detail", args=[self.object.pk]
                ),
            }
        )
        return context
