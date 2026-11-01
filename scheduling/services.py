"""Transactional section rules.

Each public service owns its ``transaction.atomic()`` block. ``IntegrityError``
is deliberately not caught here: it propagates after the transaction rolls
back so views can present the shared, readable conflict message.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from academics.models import Instructor
from scheduling.models import Room, Section

# Imported lazily where required to keep the scheduling/enrollment coupling
# limited to a single direction at module import time.
_UNSET = object()


def _resolve_instructor(instructor):
    if instructor is None:
        return None
    return instructor if isinstance(instructor, Instructor) else Instructor.objects.get(pk=instructor)


def _instructor_has_conflict(
    *, instructor, term, day_of_week, start_time, end_time, exclude_section_id=None
):
    """Return True when the instructor teaches an overlapping section.

    CANCELLED sections do not occupy time. CLOSED sections still do.
    """
    if instructor is None or day_of_week is None or start_time is None or end_time is None:
        return False
    conflicts = Section.objects.filter(
        instructor=instructor,
        term=term,
        day_of_week=day_of_week,
        start_time__lt=end_time,
        end_time__gt=start_time,
    ).exclude(status=Section.Status.CANCELLED)
    if exclude_section_id is not None:
        conflicts = conflicts.exclude(pk=exclude_section_id)
    return conflicts.exists()


def _room_has_conflict(
    *, room, term, day_of_week, start_time, end_time, exclude_section_id=None
):
    """Return True when another non-cancelled section books the same room.

    A TBA room (``room is None``) or an incomplete (TBA) schedule never
    conflicts. CANCELLED sections do not occupy a room. Adjacent slots are
    allowed because the overlap test is strict (``start < other_end`` and
    ``end > other_start``).
    """
    if room is None or day_of_week is None or start_time is None or end_time is None:
        return False
    conflicts = Section.objects.filter(
        room=room,
        term=term,
        day_of_week=day_of_week,
        start_time__lt=end_time,
        end_time__gt=start_time,
    ).exclude(status=Section.Status.CANCELLED)
    if exclude_section_id is not None:
        conflicts = conflicts.exclude(pk=exclude_section_id)
    return conflicts.exists()


def _active_enrolled_details(section_id):
    from enrollment.models import Enrollment, EnrollmentDetail

    return EnrollmentDetail.objects.filter(
        section_id=section_id,
        status=EnrollmentDetail.Status.ENROLLED,
    ).exclude(enrollment__status=Enrollment.Status.CANCELLED)


def _schedule_conflict_for_enrolled_students(*, section, day_of_week, start_time, end_time):
    """Return enrolled students whose other sections overlap the new schedule.

    Only called when the candidate schedule is complete. TBA schedules are
    handled by the caller because they cannot be compared.
    """
    from enrollment.models import Enrollment, EnrollmentDetail

    enrolled = list(
        _active_enrolled_details(section.pk).select_related("enrollment")
    )
    conflicting_students = []
    for detail in enrolled:
        other = (
            EnrollmentDetail.objects.filter(
                enrollment__student_id=detail.enrollment.student_id,
                enrollment__term_id=section.term_id,
                status=EnrollmentDetail.Status.ENROLLED,
                section__day_of_week=day_of_week,
                section__start_time__lt=end_time,
                section__end_time__gt=start_time,
            )
            .exclude(section_id=section.pk)
            .exclude(enrollment__status=Enrollment.Status.CANCELLED)
        )
        if other.exists():
            conflicting_students.append(detail.enrollment.student_id)
    return conflicting_students


def _validate_instructor(instructor):
    if instructor is None:
        return
    if not instructor.user.is_active:
        raise ValidationError(
            "The selected instructor account is inactive."
        )
    from accounts.models import User

    if instructor.user.role != User.Role.INSTRUCTOR:
        raise ValidationError(
            "The selected account does not have an instructor profile."
        )


def _validate_schedule_values(day_of_week, start_time, end_time):
    supplied = [value is not None for value in (day_of_week, start_time, end_time)]
    if any(supplied) and not all(supplied):
        raise ValidationError(
            "Day, start time, and end time must all be provided together, or "
            "all left blank for a TBA section."
        )
    if all(supplied):
        if day_of_week < 0 or day_of_week > 6:
            raise ValidationError("Select a valid day of the week.")
        if end_time <= start_time:
            raise ValidationError("End time must be later than start time.")


def _validate_capacity(capacity):
    if capacity < 1:
        raise ValidationError("Capacity must be at least 1.")


def create_section(
    *,
    course,
    term,
    section_code,
    capacity,
    instructor=None,
    room=None,
    room_code="",
    day_of_week=None,
    start_time=None,
    end_time=None,
    status=Section.Status.OPEN,
):
    """Create a section after validating cross-row scheduling rules."""
    instructor = _resolve_instructor(instructor)
    with transaction.atomic():
        if instructor is not None:
            # Serialize section creation per instructor so two concurrent
            # requests cannot both pass the conflict check.
            instructor = Instructor.objects.select_for_update().get(pk=instructor.pk)
        if room is not None:
            # Serialize per room so concurrent requests cannot both pass the
            # room double-booking check.
            room = Room.objects.select_for_update().get(pk=room.pk)
        _validate_instructor(instructor)
        _validate_schedule_values(day_of_week, start_time, end_time)
        _validate_capacity(capacity)
        if _instructor_has_conflict(
            instructor=instructor,
            term=term,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
        ):
            raise ValidationError(
                "This instructor already has an overlapping section on the "
                "selected day and time in this academic term."
            )
        if _room_has_conflict(
            room=room,
            term=term,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
        ):
            raise ValidationError(
                "This room is already booked for an overlapping time on the "
                "selected day in this academic term."
            )
        section = Section(
            course=course,
            term=term,
            section_code=section_code,
            capacity=capacity,
            instructor=instructor,
            room=room,
            room_code=room_code,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            status=status,
        )
        section.save()
    return section


def update_section(
    section,
    *,
    course=_UNSET,
    term=_UNSET,
    section_code=_UNSET,
    capacity=_UNSET,
    instructor=_UNSET,
    room=_UNSET,
    room_code=_UNSET,
    day_of_week=_UNSET,
    start_time=_UNSET,
    end_time=_UNSET,
    status=_UNSET,
):
    """Update a section, protecting existing enrollment data.

    Fields left unset keep their current value. Passing ``instructor=None`` or
    a blank schedule explicitly clears it.
    """
    with transaction.atomic():
        section = Section.objects.select_for_update().get(pk=section.pk)

        instructor_value = section.instructor if instructor is _UNSET else instructor
        instructor = _resolve_instructor(instructor_value)
        if instructor is not None:
            instructor = Instructor.objects.select_for_update().get(pk=instructor.pk)
        _validate_instructor(instructor)

        room_obj = section.room if room is _UNSET else room
        if room_obj is not None:
            room_obj = Room.objects.select_for_update().get(pk=room_obj.pk)

        new_course = section.course if course is _UNSET else course
        new_term = section.term if term is _UNSET else term
        new_code = section.section_code if section_code is _UNSET else section_code
        new_capacity = section.capacity if capacity is _UNSET else capacity
        new_room = section.room_code if room_code is _UNSET else room_code
        new_day = section.day_of_week if day_of_week is _UNSET else day_of_week
        new_start = section.start_time if start_time is _UNSET else start_time
        new_end = section.end_time if end_time is _UNSET else end_time
        new_status = section.status if status is _UNSET else status

        from enrollment.models import EnrollmentDetail

        has_details = EnrollmentDetail.objects.filter(section=section).exists()
        active_enrolled = _active_enrolled_details(section.pk)

        if has_details and (
            new_course.pk != section.course_id or new_term.pk != section.term_id
        ):
            raise ValidationError(
                "The course and academic term cannot be changed because this "
                "section already has enrollment records."
            )

        if new_capacity < active_enrolled.count():
            raise ValidationError(
                "Capacity cannot be reduced below the number of currently "
                "enrolled students."
            )
        _validate_capacity(new_capacity)

        if new_status == Section.Status.CANCELLED and active_enrolled.exists():
            raise ValidationError(
                "This section cannot be cancelled while it has enrolled "
                "students. Remove or transfer them through the enrollment "
                "workflow first."
            )

        schedule_complete = (
            new_day is not None and new_start is not None and new_end is not None
        )
        _validate_schedule_values(new_day, new_start, new_end)

        if active_enrolled.exists() and not schedule_complete:
            raise ValidationError(
                "A section with enrolled students must keep a complete schedule."
            )

        if _instructor_has_conflict(
            instructor=instructor,
            term=new_term,
            day_of_week=new_day,
            start_time=new_start,
            end_time=new_end,
            exclude_section_id=section.pk,
        ):
            raise ValidationError(
                "This instructor already has an overlapping section on the "
                "selected day and time in this academic term."
            )

        if _room_has_conflict(
            room=room_obj,
            term=new_term,
            day_of_week=new_day,
            start_time=new_start,
            end_time=new_end,
            exclude_section_id=section.pk,
        ):
            raise ValidationError(
                "This room is already booked for an overlapping time on the "
                "selected day in this academic term."
            )

        if (
            schedule_complete
            and active_enrolled.exists()
            and (new_day, new_start, new_end)
            != (section.day_of_week, section.start_time, section.end_time)
        ):
            conflicting_students = _schedule_conflict_for_enrolled_students(
                section=section,
                day_of_week=new_day,
                start_time=new_start,
                end_time=new_end,
            )
            if conflicting_students:
                raise ValidationError(
                    "The new schedule conflicts with other registered sections "
                    f"for {len(conflicting_students)} enrolled student(s)."
                )

        section.course = new_course
        section.term = new_term
        section.section_code = new_code
        section.capacity = new_capacity
        section.instructor = instructor
        section.room = room_obj
        section.room_code = new_room
        section.day_of_week = new_day
        section.start_time = new_start
        section.end_time = new_end
        section.status = new_status
        section.save()
    return section
