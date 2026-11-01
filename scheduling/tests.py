from datetime import time
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from accounts.services import CONFLICT_ERROR
from academics.models import (
    AcademicTerm,
    College,
    Course,
    Curriculum,
    Instructor,
    Program,
    Student,
)
from enrollment.models import Enrollment, EnrollmentDetail
from scheduling.models import Section


class SchedulingTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.college = College.objects.create(
            college_code="SCH-ENG", name="Scheduling College"
        )
        cls.program = Program.objects.create(
            college=cls.college,
            program_code="SCH-BS",
            name="Scheduling Program",
        )
        cls.curriculum = Curriculum.objects.create(
            program=cls.program,
            curriculum_code="SCH-CUR",
            effective_year=2024,
        )
        cls.course1 = Course.objects.create(
            course_code="SCH101", title="Scheduling 1", units=3
        )
        cls.course2 = Course.objects.create(
            course_code="SCH102", title="Scheduling 2", units=3
        )
        cls.term1 = AcademicTerm.objects.create(
            academic_year="2026-2027",
            semester_number=1,
            start_date="2026-08-01",
            end_date="2026-12-15",
            enrollment_open=True,
        )
        cls.term2 = AcademicTerm.objects.create(
            academic_year="2026-2027",
            semester_number=2,
            start_date="2027-01-05",
            end_date="2027-05-20",
            enrollment_open=True,
        )
        cls.instructor_user = User.objects.create_user(
            username="sch_instructor",
            password="pass12345",
            role=User.Role.INSTRUCTOR,
            first_name="Sched",
            last_name="Instructor",
        )
        cls.instructor = Instructor.objects.create(
            user=cls.instructor_user, employee_number="SCH-EMP-1"
        )
        cls.other_instructor_user = User.objects.create_user(
            username="sch_instructor_2",
            password="pass12345",
            role=User.Role.INSTRUCTOR,
            first_name="Other",
            last_name="Instructor",
        )
        cls.other_instructor = Instructor.objects.create(
            user=cls.other_instructor_user, employee_number="SCH-EMP-2"
        )
        cls.inactive_instructor_user = User.objects.create_user(
            username="sch_inactive_instructor",
            password="pass12345",
            role=User.Role.INSTRUCTOR,
            is_active=False,
        )
        cls.inactive_instructor = Instructor.objects.create(
            user=cls.inactive_instructor_user, employee_number="SCH-EMP-3"
        )
        cls.registrar = User.objects.create_user(
            username="sch_registrar",
            password="pass12345",
            role=User.Role.REGISTRAR,
        )
        cls.administrator = User.objects.create_user(
            username="sch_administrator",
            password="pass12345",
            role=User.Role.ADMINISTRATOR,
            is_staff=True,
        )
        cls.cashier = User.objects.create_user(
            username="sch_cashier",
            password="pass12345",
            role=User.Role.CASHIER,
        )
        cls.student_user = User.objects.create_user(
            username="sch_student",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        cls.student = Student.objects.create(
            user=cls.student_user,
            student_number="SCH-2026-001",
            curriculum=cls.curriculum,
            year_level=1,
        )
        cls.inactive_registrar = User.objects.create_user(
            username="sch_inactive_registrar",
            password="pass12345",
            role=User.Role.REGISTRAR,
            is_active=False,
        )
        cls.section = Section.objects.create(
            course=cls.course1,
            term=cls.term1,
            instructor=cls.instructor,
            section_code="A1",
            capacity=30,
            room_code="R101",
            day_of_week=Section.DayOfWeek.MONDAY,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

    def section_payload(self, **overrides):
        data = {
            "course": self.course1.pk,
            "term": self.term1.pk,
            "instructor": self.instructor.pk,
            "section_code": "NEW1",
            "capacity": 25,
            "room_code": "R202",
            "day_of_week": Section.DayOfWeek.WEDNESDAY,
            "start_time": "10:00",
            "end_time": "11:00",
            "status": Section.Status.OPEN,
        }
        data.update(overrides)
        return data

    def make_enrollment(self, student=None, term=None, status=None):
        return Enrollment.objects.create(
            student=student or self.student,
            term=term or self.term1,
            status=status or Enrollment.Status.DRAFT,
        )

    def make_detail(self, enrollment, section, status=EnrollmentDetail.Status.ENROLLED):
        return EnrollmentDetail.objects.create(
            enrollment=enrollment,
            section=section,
            status=status,
        )


class SectionAuthorizationTests(SchedulingTestBase):
    def test_registrar_can_access_all_section_screens(self):
        self.client.force_login(self.registrar)
        urls = [
            reverse("scheduling:section_list"),
            reverse("scheduling:section_create"),
            reverse("scheduling:section_detail", args=[self.section.pk]),
            reverse("scheduling:section_update", args=[self.section.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_administrator_has_read_only_access(self):
        self.client.force_login(self.administrator)
        self.assertEqual(
            self.client.get(reverse("scheduling:section_list")).status_code, 200
        )
        self.assertEqual(
            self.client.get(
                reverse("scheduling:section_detail", args=[self.section.pk])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("scheduling:section_create")).status_code, 403
        )
        self.assertEqual(
            self.client.get(
                reverse("scheduling:section_update", args=[self.section.pk])
            ).status_code,
            403,
        )
        response = self.client.post(
            reverse("scheduling:section_create"), self.section_payload()
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Section.objects.filter(section_code="NEW1").exists())

    def test_other_roles_are_denied(self):
        for user in (self.cashier, self.student_user, self.instructor_user):
            self.client.force_login(user)
            with self.subTest(role=user.role):
                self.assertEqual(
                    self.client.get(reverse("scheduling:section_list")).status_code,
                    403,
                )
                self.assertEqual(
                    self.client.get(reverse("scheduling:section_create")).status_code,
                    403,
                )

    def test_anonymous_redirected_to_login_with_next(self):
        response = self.client.get(reverse("scheduling:section_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        self.assertIn("next=", response.url)

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.AllowAllUsersModelBackend",
        ]
    )
    def test_inactive_registrar_is_denied(self):
        self.client.force_login(self.inactive_registrar)
        urls = [
            reverse("scheduling:section_list"),
            reverse("scheduling:section_create"),
            reverse("scheduling:section_detail", args=[self.section.pk]),
            reverse("scheduling:section_update", args=[self.section.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)


class SectionWorkflowTests(SchedulingTestBase):
    def setUp(self):
        self.client.force_login(self.registrar)

    def test_registrar_can_create_section(self):
        response = self.client.post(
            reverse("scheduling:section_create"), self.section_payload()
        )
        self.assertEqual(response.status_code, 302)
        section = Section.objects.get(section_code="NEW1")
        self.assertEqual(section.capacity, 25)
        self.assertEqual(section.instructor, self.instructor)
        self.assertRedirects(
            response, reverse("scheduling:section_detail", args=[section.pk])
        )

    def test_registrar_can_create_tba_section(self):
        response = self.client.post(
            reverse("scheduling:section_create"),
            self.section_payload(
                section_code="TBA1",
                day_of_week="",
                start_time="",
                end_time="",
                instructor="",
            ),
        )
        self.assertEqual(response.status_code, 302)
        section = Section.objects.get(section_code="TBA1")
        self.assertIsNone(section.day_of_week)
        self.assertIsNone(section.start_time)
        self.assertIsNone(section.end_time)
        self.assertIsNone(section.instructor)

    def test_registrar_can_update_section(self):
        response = self.client.post(
            reverse("scheduling:section_update", args=[self.section.pk]),
            self.section_payload(
                section_code=self.section.section_code,
                course=self.course1.pk,
                term=self.term1.pk,
                capacity=40,
                room_code="R999",
                day_of_week=Section.DayOfWeek.MONDAY,
                start_time="08:00",
                end_time="09:00",
            ),
        )
        self.assertEqual(response.status_code, 302)
        self.section.refresh_from_db()
        self.assertEqual(self.section.capacity, 40)
        self.assertEqual(self.section.room_code, "R999")

    def test_duplicate_section_code_is_rejected_readably(self):
        response = self.client.post(
            reverse("scheduling:section_create"),
            self.section_payload(
                section_code="A1",
                day_of_week=Section.DayOfWeek.THURSDAY,
                start_time="13:00",
                end_time="14:00",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertEqual(Section.objects.filter(section_code="A1").count(), 1)

    def test_zero_capacity_is_rejected(self):
        response = self.client.post(
            reverse("scheduling:section_create"), self.section_payload(capacity=0)
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "at least 1")

    def test_partial_schedule_is_rejected(self):
        response = self.client.post(
            reverse("scheduling:section_create"),
            self.section_payload(day_of_week=Section.DayOfWeek.MONDAY, start_time="", end_time=""),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "all be provided together")
        self.assertFalse(Section.objects.filter(section_code="NEW1").exists())

    def test_end_time_must_be_later_than_start(self):
        response = self.client.post(
            reverse("scheduling:section_create"),
            self.section_payload(start_time="11:00", end_time="10:00"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "later than start time")

    def test_invalid_day_of_week_is_rejected(self):
        response = self.client.post(
            reverse("scheduling:section_create"), self.section_payload(day_of_week=9)
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Section.objects.filter(section_code="NEW1").exists())

    def test_instructor_overlap_is_rejected(self):
        response = self.client.post(
            reverse("scheduling:section_create"),
            self.section_payload(
                day_of_week=Section.DayOfWeek.MONDAY,
                start_time="08:30",
                end_time="09:30",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "overlapping section")
        self.assertFalse(Section.objects.filter(section_code="NEW1").exists())

    def test_back_to_back_schedule_is_allowed(self):
        response = self.client.post(
            reverse("scheduling:section_create"),
            self.section_payload(
                day_of_week=Section.DayOfWeek.MONDAY,
                start_time="09:00",
                end_time="10:00",
            ),
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Section.objects.filter(section_code="NEW1").exists())

    def test_different_day_is_allowed(self):
        response = self.client.post(
            reverse("scheduling:section_create"),
            self.section_payload(
                day_of_week=Section.DayOfWeek.TUESDAY,
                start_time="08:00",
                end_time="09:00",
            ),
        )
        self.assertEqual(response.status_code, 302)

    def test_different_term_is_allowed(self):
        response = self.client.post(
            reverse("scheduling:section_create"),
            self.section_payload(
                term=self.term2.pk,
                day_of_week=Section.DayOfWeek.MONDAY,
                start_time="08:00",
                end_time="09:00",
            ),
        )
        self.assertEqual(response.status_code, 302)

    def test_cancelled_sections_do_not_block_instructor(self):
        Section.objects.create(
            course=self.course2,
            term=self.term1,
            instructor=self.instructor,
            section_code="CXL",
            capacity=10,
            day_of_week=Section.DayOfWeek.MONDAY,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Section.Status.CANCELLED,
        )
        response = self.client.post(
            reverse("scheduling:section_create"),
            self.section_payload(
                course=self.course2.pk,
                section_code="NEW2",
                day_of_week=Section.DayOfWeek.MONDAY,
                start_time="10:15",
                end_time="10:45",
            ),
        )
        self.assertEqual(response.status_code, 302)

    def test_update_does_not_conflict_with_itself(self):
        response = self.client.post(
            reverse("scheduling:section_update", args=[self.section.pk]),
            self.section_payload(
                section_code=self.section.section_code,
                course=self.course1.pk,
                term=self.term1.pk,
                capacity=31,
                day_of_week=Section.DayOfWeek.MONDAY,
                start_time="08:00",
                end_time="09:00",
            ),
        )
        self.assertEqual(response.status_code, 302)

    def test_inactive_instructor_is_rejected(self):
        response = self.client.post(
            reverse("scheduling:section_create"),
            self.section_payload(instructor=self.inactive_instructor.pk),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "inactive")
        self.assertFalse(Section.objects.filter(section_code="NEW1").exists())

    def test_capacity_cannot_drop_below_enrolled_count(self):
        other_student_user = User.objects.create_user(
            username="sch_student_2",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        other_student = Student.objects.create(
            user=other_student_user,
            student_number="SCH-2026-002",
            curriculum=self.curriculum,
            year_level=1,
        )
        self.make_detail(self.make_enrollment(), self.section)
        self.make_detail(
            self.make_enrollment(student=other_student), self.section
        )
        response = self.client.post(
            reverse("scheduling:section_update", args=[self.section.pk]),
            self.section_payload(
                section_code=self.section.section_code,
                course=self.course1.pk,
                term=self.term1.pk,
                capacity=1,
                day_of_week=Section.DayOfWeek.MONDAY,
                start_time="08:00",
                end_time="09:00",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Capacity cannot be reduced")
        self.section.refresh_from_db()
        self.assertEqual(self.section.capacity, 30)

    def test_course_and_term_cannot_change_when_details_exist(self):
        self.make_detail(self.make_enrollment(), self.section)
        response = self.client.post(
            reverse("scheduling:section_update", args=[self.section.pk]),
            self.section_payload(
                section_code=self.section.section_code,
                course=self.course2.pk,
                term=self.term1.pk,
                day_of_week=Section.DayOfWeek.MONDAY,
                start_time="08:00",
                end_time="09:00",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot be changed")
        self.section.refresh_from_db()
        self.assertEqual(self.section.course_id, self.course1.pk)

    def test_section_with_enrolled_students_cannot_be_cancelled(self):
        self.make_detail(self.make_enrollment(), self.section)
        response = self.client.post(
            reverse("scheduling:section_update", args=[self.section.pk]),
            self.section_payload(
                section_code=self.section.section_code,
                course=self.course1.pk,
                term=self.term1.pk,
                day_of_week=Section.DayOfWeek.MONDAY,
                start_time="08:00",
                end_time="09:00",
                status=Section.Status.CANCELLED,
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot be cancelled")
        self.section.refresh_from_db()
        self.assertEqual(self.section.status, Section.Status.OPEN)

    def test_section_without_students_can_be_cancelled(self):
        empty_section = Section.objects.create(
            course=self.course2,
            term=self.term1,
            instructor=self.other_instructor,
            section_code="EMPTY",
            capacity=20,
            day_of_week=Section.DayOfWeek.THURSDAY,
            start_time=time(13, 0),
            end_time=time(14, 0),
        )
        response = self.client.post(
            reverse("scheduling:section_update", args=[empty_section.pk]),
            self.section_payload(
                course=self.course2.pk,
                term=self.term1.pk,
                section_code="EMPTY",
                instructor=self.other_instructor.pk,
                day_of_week=Section.DayOfWeek.THURSDAY,
                start_time="13:00",
                end_time="14:00",
                status=Section.Status.CANCELLED,
            ),
        )
        self.assertEqual(response.status_code, 302)
        empty_section.refresh_from_db()
        self.assertEqual(empty_section.status, Section.Status.CANCELLED)

    def test_section_with_enrolled_students_cannot_become_tba(self):
        self.make_detail(self.make_enrollment(), self.section)
        response = self.client.post(
            reverse("scheduling:section_update", args=[self.section.pk]),
            self.section_payload(
                section_code=self.section.section_code,
                course=self.course1.pk,
                term=self.term1.pk,
                day_of_week="",
                start_time="",
                end_time="",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "must keep a complete schedule")

    def test_schedule_change_causing_student_conflict_is_rejected(self):
        enrollment = self.make_enrollment()
        self.make_detail(enrollment, self.section)
        other_section = Section.objects.create(
            course=self.course2,
            term=self.term1,
            instructor=self.other_instructor,
            section_code="B1",
            capacity=20,
            day_of_week=Section.DayOfWeek.MONDAY,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )
        self.make_detail(enrollment, other_section)

        response = self.client.post(
            reverse("scheduling:section_update", args=[self.section.pk]),
            self.section_payload(
                section_code=self.section.section_code,
                course=self.course1.pk,
                term=self.term1.pk,
                instructor=self.instructor.pk,
                day_of_week=Section.DayOfWeek.MONDAY,
                start_time="10:30",
                end_time="11:30",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "conflicts with other registered sections")
        self.section.refresh_from_db()
        self.assertEqual(self.section.start_time, time(8, 0))


class SectionIntegrityErrorTests(SchedulingTestBase):
    def setUp(self):
        self.client.force_login(self.registrar)

    def test_create_integrity_error_is_handled(self):
        with patch.object(Section, "save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(
                reverse("scheduling:section_create"), self.section_payload()
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        self.assertFalse(Section.objects.filter(section_code="NEW1").exists())
        Section.objects.create(
            course=self.course2,
            term=self.term1,
            section_code="AFTER",
            capacity=10,
        )
        self.assertTrue(Section.objects.filter(section_code="AFTER").exists())

    def test_update_integrity_error_is_handled(self):
        with patch.object(Section, "save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(
                reverse("scheduling:section_update", args=[self.section.pk]),
                self.section_payload(
                    section_code=self.section.section_code,
                    course=self.course1.pk,
                    term=self.term1.pk,
                    capacity=99,
                    day_of_week=Section.DayOfWeek.MONDAY,
                    start_time="08:00",
                    end_time="09:00",
                ),
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        self.section.refresh_from_db()
        self.assertEqual(self.section.capacity, 30)

    def test_integrity_error_response_does_not_leak_database_details(self):
        with patch.object(Section, "save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(
                reverse("scheduling:section_create"), self.section_payload()
            )
        content = response.content.decode()
        self.assertNotIn("IntegrityError", content)
        self.assertNotIn("Duplicate entry", content)
        self.assertNotIn("INSERT INTO", content)
        self.assertNotIn("Traceback", content)
