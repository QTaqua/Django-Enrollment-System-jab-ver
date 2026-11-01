"""Registrar enrollment screens and the student enrollment portal.

Services own their transactions. Views map cleaned data explicitly and catch
``IntegrityError`` only after the service has rolled back.
"""

import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.models import User
from accounts.permissions import (
    RegistrarReadOnlyMixin,
    RegistrarRequiredMixin,
    RoleRequiredMixin,
    get_student_for_user,
)
from accounts.services import CONFLICT_ERROR
from enrollment.forms import AddSectionForm, EnrollmentCreateForm
from enrollment.models import Enrollment, EnrollmentDetail
from enrollment.services import (
    confirm_enrollment,
    create_enrollment,
    drop_enrollment_detail,
    enroll_in_section,
)

logger = logging.getLogger(__name__)


def _enrollment_queryset():
    return Enrollment.objects.select_related(
        "student__user", "term"
    ).prefetch_related(
        "details__section__course",
        "details__section__instructor__user",
    )


def _details_queryset(enrollment):
    return (
        EnrollmentDetail.objects.filter(enrollment=enrollment)
        .select_related(
            "section__course",
            "section__term",
            "section__instructor__user",
        )
        .order_by("section__course__course_code", "section__section_code")
    )


class EnrollmentListView(RegistrarReadOnlyMixin, ListView):
    model = Enrollment
    template_name = "enrollment/enrollment_list.html"
    context_object_name = "enrollments"

    def get_queryset(self):
        return (
            _enrollment_queryset()
            .annotate(
                active_section_count=Count(
                    "details",
                    filter=Q(
                        details__status=EnrollmentDetail.Status.ENROLLED
                    )
                    & ~Q(
                        details__enrollment__status=Enrollment.Status.CANCELLED
                    ),
                    distinct=True,
                )
            )
            .order_by("-term__academic_year", "term__semester_number", "student__student_number")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_manage"] = (
            getattr(self.request.user, "role", None) == User.Role.REGISTRAR
        )
        return context


class EnrollmentDetailView(RegistrarReadOnlyMixin, DetailView):
    model = Enrollment
    template_name = "enrollment/enrollment_detail.html"
    context_object_name = "enrollment"

    def get_queryset(self):
        return _enrollment_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollment = self.object
        details = list(_details_queryset(enrollment))
        context.update(
            {
                "details": details,
                "active_detail_count": sum(
                    1
                    for detail in details
                    if detail.status == EnrollmentDetail.Status.ENROLLED
                ),
                "can_manage": getattr(self.request.user, "role", None)
                == User.Role.REGISTRAR,
                "back_url": reverse("enrollment:enrollment_list"),
            }
        )
        return context


class EnrollmentCreateView(RegistrarRequiredMixin, View):
    template_name = "enrollment/enrollment_form.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "form": EnrollmentCreateForm(),
                "title": "Add Enrollment",
                "cancel_url": reverse("enrollment:enrollment_list"),
            },
        )

    def post(self, request):
        form = EnrollmentCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                enrollment = create_enrollment(
                    student=data["student"], term=data["term"]
                )
            except ValidationError as exc:
                form.add_error(None, exc.messages)
            except IntegrityError:
                logger.warning(
                    "Integrity conflict creating enrollment in %s",
                    self.__class__.__name__,
                )
                form.add_error(None, CONFLICT_ERROR)
            else:
                messages.success(request, "Draft enrollment created successfully.")
                return redirect(
                    "enrollment:enrollment_detail", pk=enrollment.pk
                )
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Add Enrollment",
                "cancel_url": reverse("enrollment:enrollment_list"),
            },
        )


class EnrollmentAddSectionView(RegistrarRequiredMixin, View):
    template_name = "enrollment/add_section_form.html"

    def get_enrollment(self, pk):
        return get_object_or_404(_enrollment_queryset(), pk=pk)

    def get(self, request, pk):
        enrollment = self.get_enrollment(pk)
        if enrollment.status != Enrollment.Status.DRAFT:
            messages.error(
                request,
                "Sections can only be added to a draft enrollment.",
            )
            return redirect(
                "enrollment:enrollment_detail", pk=enrollment.pk
            )
        return self.render_form(request, enrollment, AddSectionForm(term=enrollment.term))

    def render_form(self, request, enrollment, form):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "enrollment": enrollment,
                "details": _details_queryset(enrollment),
                "cancel_url": reverse(
                    "enrollment:enrollment_detail", args=[enrollment.pk]
                ),
            },
        )

    def post(self, request, pk):
        enrollment = self.get_enrollment(pk)
        form = AddSectionForm(request.POST, term=enrollment.term)
        if form.is_valid():
            try:
                enroll_in_section(
                    enrollment=enrollment, section=form.cleaned_data["section"]
                )
            except ValidationError as exc:
                form.add_error(None, exc.messages)
            except IntegrityError:
                logger.warning(
                    "Integrity conflict adding section in %s",
                    self.__class__.__name__,
                )
                form.add_error(None, CONFLICT_ERROR)
            else:
                messages.success(request, "Section added to the enrollment.")
                return redirect(
                    "enrollment:enrollment_detail", pk=enrollment.pk
                )
        return self.render_form(request, enrollment, form)


class EnrollmentConfirmView(RegistrarRequiredMixin, View):
    def post(self, request, pk):
        enrollment = get_object_or_404(Enrollment, pk=pk)
        try:
            confirm_enrollment(enrollment=enrollment)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        except IntegrityError:
            logger.warning(
                "Integrity conflict confirming enrollment in %s",
                self.__class__.__name__,
            )
            messages.error(request, CONFLICT_ERROR)
        else:
            messages.success(request, "Enrollment confirmed successfully.")
            # A DRAFT assessment is created automatically on confirmation; it is
            # never auto-finalized. Failures here do not undo the confirmation.
            try:
                from finance.services import create_draft_assessment

                create_draft_assessment(enrollment=enrollment, by=request.user)
            except ValidationError as exc:
                messages.warning(
                    request,
                    "Enrollment confirmed, but a draft assessment could not be "
                    "created: " + " ".join(exc.messages),
                )
        return redirect("enrollment:enrollment_detail", pk=enrollment.pk)


class EnrollmentRemoveSectionView(RegistrarRequiredMixin, View):
    def post(self, request, pk, detail_pk):
        enrollment = get_object_or_404(Enrollment, pk=pk)
        detail = get_object_or_404(
            EnrollmentDetail, pk=detail_pk, enrollment=enrollment
        )
        withdrawn = request.POST.get("withdrawn") == "1"
        try:
            drop_enrollment_detail(detail=detail, withdrawn=withdrawn)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        except IntegrityError:
            logger.warning(
                "Integrity conflict removing section in %s",
                self.__class__.__name__,
            )
            messages.error(request, CONFLICT_ERROR)
        else:
            messages.success(request, "Section removed from the enrollment.")
        return redirect("enrollment:enrollment_detail", pk=enrollment.pk)


class MyEnrollmentListView(RoleRequiredMixin, ListView):
    model = Enrollment
    template_name = "enrollment/my_enrollments.html"
    context_object_name = "enrollments"
    allowed_roles = (User.Role.STUDENT,)

    def get_queryset(self):
        student = get_student_for_user(self.request.user)
        if student is None:
            return Enrollment.objects.none()
        return (
            Enrollment.objects.filter(student=student)
            .select_related("term")
            .prefetch_related(
                "details__section__course",
                "details__section__instructor__user",
            )
            .order_by("-term__academic_year", "term__semester_number")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["student"] = get_student_for_user(self.request.user)
        return context


class MyEnrollmentDetailView(RoleRequiredMixin, DetailView):
    model = Enrollment
    template_name = "enrollment/enrollment_detail.html"
    context_object_name = "enrollment"
    allowed_roles = (User.Role.STUDENT,)

    def get_object(self, queryset=None):
        student = get_student_for_user(self.request.user)
        if student is None:
            from django.http import Http404

            raise Http404("No student profile is associated with this account.")
        return get_object_or_404(
            _enrollment_queryset(),
            pk=self.kwargs["pk"],
            student=student,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        details = list(_details_queryset(self.object))
        context.update(
            {
                "details": details,
                "active_detail_count": sum(
                    1
                    for detail in details
                    if detail.status == EnrollmentDetail.Status.ENROLLED
                ),
                "can_manage": False,
                "back_url": reverse("enrollment:my_enrollment_list"),
            }
        )
        return context
