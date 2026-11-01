"""Transactional enrollment rules that cannot be expressed as row constraints.

Each public service owns its ``transaction.atomic()`` block. ``IntegrityError``
is never caught here: it propagates after rollback so views can present the
shared, readable conflict message.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from academics.models import AcademicTerm, Course, CoursePrerequisite, CurriculumCourse, Student
from scheduling.models import Section

from .models import Enrollment, EnrollmentDetail

# Statuses that still occupy a course slot for duplicate-course checks.
BLOCKING_DETAIL_STATUSES = (
    EnrollmentDetail.Status.ENROLLED,
    EnrollmentDetail.Status.COMPLETED,
)


def _active_details(enrollment):
    """Details that still count as registered for this enrollment."""
    return EnrollmentDetail.objects.filter(
        enrollment=enrollment,
        status=EnrollmentDetail.Status.ENROLLED,
    )


def passed_course_ids(student, *, exclude_term=None):
    """Return course ids the student has explicitly completed and passed.

    Only ``COMPLETED`` + ``PASSED`` qualifies. Numeric grades are never
    consulted. Results from cancelled enrollments are ignored, and results
    from ``exclude_term`` (the term being enrolled in) do not count.
    """
    queryset = EnrollmentDetail.objects.filter(
        enrollment__student=student,
        status=EnrollmentDetail.Status.COMPLETED,
        result_status=EnrollmentDetail.ResultStatus.PASSED,
    ).exclude(enrollment__status=Enrollment.Status.CANCELLED)
    if exclude_term is not None:
        queryset = queryset.exclude(enrollment__term=exclude_term)
    return set(
        queryset.values_list("section__course_id", flat=True)
    )


def missing_prerequisites(student, course, *, term=None):
    """Return prerequisite courses the student has not completed and passed.

    Enrollment in, or merely passing, a course is not sufficient: the detail
    must be both ``COMPLETED`` and ``PASSED``. A result from the target term is
    never treated as already completed.
    """
    required_ids = set(
        CoursePrerequisite.objects.filter(course=course).values_list(
            "prerequisite_course_id", flat=True
        )
    )
    if not required_ids:
        return []
    passed_ids = passed_course_ids(student, exclude_term=term)
    missing_ids = required_ids - passed_ids
    return list(Course.objects.filter(pk__in=missing_ids).order_by("course_code"))


def _section_has_complete_schedule(section):
    return (
        section.day_of_week is not None
        and section.start_time is not None
        and section.end_time is not None
    )


def _student_schedule_conflict(*, enrollment, section):
    """Return an overlapping detail for the same student and term, if any.

    Sections already added to the draft enrollment being modified are
    included: a student cannot register two overlapping classes even inside
    one enrollment. The section being added has no detail row yet.
    """
    return (
        EnrollmentDetail.objects.filter(
            enrollment__student_id=enrollment.student_id,
            enrollment__term_id=enrollment.term_id,
            status=EnrollmentDetail.Status.ENROLLED,
            section__day_of_week=section.day_of_week,
            section__start_time__lt=section.end_time,
            section__end_time__gt=section.start_time,
        )
        .exclude(enrollment__status=Enrollment.Status.CANCELLED)
        .select_related("section__course")
        .first()
    )


def _section_enrolled_count(section):
    return (
        EnrollmentDetail.objects.filter(
            section=section,
            status=EnrollmentDetail.Status.ENROLLED,
        )
        .exclude(enrollment__status=Enrollment.Status.CANCELLED)
        .count()
    )


@transaction.atomic
def create_enrollment(*, student, term):
    """Create one DRAFT enrollment for a student and open academic term."""
    student = Student.objects.select_for_update().select_related("user").get(
        pk=student.pk
    )
    term = AcademicTerm.objects.get(pk=term.pk)

    if not student.user.is_active:
        raise ValidationError(
            "The selected student account is inactive and cannot be enrolled."
        )
    if not term.enrollment_open:
        raise ValidationError(
            "Enrollment is not open for the selected academic term."
        )
    if Enrollment.objects.filter(student=student, term=term).exists():
        raise ValidationError(
            "This student already has an enrollment for the selected academic "
            "term. A replacement enrollment cannot be created."
        )

    return Enrollment.objects.create(
        student=student, term=term, status=Enrollment.Status.DRAFT
    )


@transaction.atomic
def enroll_in_section(*, enrollment, section):
    """Add a section to a DRAFT enrollment after validating every rule.

    Locks the enrollment and section rows so concurrent requests through this
    service cannot both pass the duplicate-course or capacity checks.
    """
    enrollment = (
        Enrollment.objects.select_for_update()
        .select_related("student__user", "term")
        .get(pk=enrollment.pk)
    )
    section = (
        Section.objects.select_for_update()
        .select_related("course", "term")
        .get(pk=section.pk)
    )

    if enrollment.status != Enrollment.Status.DRAFT:
        raise ValidationError(
            "Sections can only be added to a draft enrollment."
        )
    if not enrollment.term.enrollment_open:
        raise ValidationError(
            "Enrollment is not open for this academic term."
        )
    if section.term_id != enrollment.term_id:
        raise ValidationError(
            "The section belongs to a different academic term."
        )
    if section.status != Section.Status.OPEN:
        raise ValidationError("The section is not open for enrollment.")
    if not _section_has_complete_schedule(section):
        raise ValidationError(
            "The section schedule is not complete (TBA). A schedule must be "
            "set before students can be enrolled."
        )

    if EnrollmentDetail.objects.filter(
        enrollment=enrollment, section=section
    ).exists():
        raise ValidationError("This section is already part of the enrollment.")

    duplicate_course = EnrollmentDetail.objects.filter(
        enrollment=enrollment,
        section__course_id=section.course_id,
        status__in=BLOCKING_DETAIL_STATUSES,
    ).exists()
    if duplicate_course:
        raise ValidationError(
            "The student is already registered in another section of this "
            "course. Multiple sections of the same course are not allowed in "
            "one enrollment."
        )

    if _section_enrolled_count(section) >= section.capacity:
        raise ValidationError("The section has reached its capacity.")

    in_curriculum = CurriculumCourse.objects.filter(
        curriculum_id=enrollment.student.curriculum_id,
        course_id=section.course_id,
    ).exists()
    if not in_curriculum:
        raise ValidationError(
            "This course is not part of the student's curriculum."
        )

    missing = missing_prerequisites(
        enrollment.student, section.course, term=enrollment.term
    )
    if missing:
        codes = ", ".join(course.course_code for course in missing)
        raise ValidationError(
            f"Prerequisite course(s) not completed and passed: {codes}."
        )

    conflict = _student_schedule_conflict(
        enrollment=enrollment, section=section
    )
    if conflict is not None:
        raise ValidationError(
            "The student already has a section at this day and time: "
            f"{conflict.section.course.course_code} "
            f"{conflict.section.section_code}."
        )

    return EnrollmentDetail.objects.create(
        enrollment=enrollment,
        section=section,
        status=EnrollmentDetail.Status.ENROLLED,
    )


@transaction.atomic
def confirm_enrollment(*, enrollment):
    """Confirm a DRAFT enrollment that has at least one active section.

    The academic term's ``enrollment_open`` flag is not re-checked: a draft
    created while enrollment was open may still be confirmed after it closes.
    """
    enrollment = Enrollment.objects.select_for_update().get(pk=enrollment.pk)
    if enrollment.status != Enrollment.Status.DRAFT:
        raise ValidationError("Only draft enrollments can be confirmed.")

    active = list(
        _active_details(enrollment)
        .select_related("section__term")
        .order_by("section_id")
    )
    if not active:
        raise ValidationError(
            "An enrollment must contain at least one section before it can be "
            "confirmed."
        )

    # Lock the referenced sections after the enrollment, in primary-key
    # order, so concurrent confirmations acquire section locks consistently.
    section_ids = sorted({detail.section_id for detail in active})
    locked_sections = {
        section.pk: section
        for section in (
            Section.objects.select_for_update()
            .filter(pk__in=section_ids)
            .order_by("pk")
        )
    }

    for detail in active:
        section = locked_sections.get(detail.section_id)
        if section is None:
            raise ValidationError(
                "One or more sections no longer exist. Refresh and try again."
            )
        if section.status == Section.Status.CANCELLED:
            raise ValidationError(
                "This enrollment includes a cancelled section. Remove or "
                "replace it before confirming."
            )
        if section.term_id != enrollment.term_id:
            raise ValidationError(
                "One or more sections belong to a different academic term."
            )
        if not _section_has_complete_schedule(section):
            raise ValidationError(
                "One or more sections do not have a complete schedule (TBA)."
            )
        if _section_enrolled_count(section) > section.capacity:
            raise ValidationError(
                "One or more sections have reached their capacity."
            )

    enrollment.status = Enrollment.Status.CONFIRMED
    enrollment.save(update_fields=["status"])
    return enrollment


@transaction.atomic
def drop_enrollment_detail(*, detail, withdrawn=False):
    """Mark a draft enrollment detail as dropped or withdrawn.

    Locks the parent enrollment first to preserve a consistent lock order with
    section addition and confirmation. The record is preserved for history;
    only DRAFT enrollments may be modified.
    """
    enrollment = Enrollment.objects.select_for_update().get(
        pk=detail.enrollment_id
    )
    detail = EnrollmentDetail.objects.select_for_update().get(pk=detail.pk)

    if enrollment.status != Enrollment.Status.DRAFT:
        raise ValidationError(
            "Sections can only be removed from a draft enrollment."
        )
    if detail.status != EnrollmentDetail.Status.ENROLLED:
        raise ValidationError(
            "Only actively enrolled sections can be removed."
        )

    detail.status = EnrollmentDetail.Status.DROPPED
    detail.result_status = (
        EnrollmentDetail.ResultStatus.WITHDRAWN
        if withdrawn
        else EnrollmentDetail.ResultStatus.DROPPED
    )
    detail.recorded_at = timezone.now()
    detail.save(update_fields=["status", "result_status", "recorded_at"])
    return detail
