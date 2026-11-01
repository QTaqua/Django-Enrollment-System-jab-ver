from datetime import time
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from accounts.services import CONFLICT_ERROR
from academics.models import (
    AcademicTerm,
    College,
    Course,
    CoursePrerequisite,
    Curriculum,
    CurriculumCourse,
    Instructor,
    Program,
    Student,
)
from enrollment.models import Enrollment, EnrollmentDetail
from enrollment.services import (
    confirm_enrollment,
    create_enrollment,
    drop_enrollment_detail,
    enroll_in_section,
    missing_prerequisites,
)
from scheduling.models import Section


class EnrollmentTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.college = College.objects.create(
            college_code="ENR-ENG", name="Enrollment College"
        )
        cls.program = Program.objects.create(
            college=cls.college,
            program_code="ENR-BS",
            name="Enrollment Program",
        )
        cls.curriculum = Curriculum.objects.create(
            program=cls.program,
            curriculum_code="ENR-CUR",
            effective_year=2024,
        )
        cls.course1 = Course.objects.create(
            course_code="ENR101", title="Enrollment 1", units=3
        )
        cls.course2 = Course.objects.create(
            course_code="ENR102", title="Enrollment 2", units=3
        )
        cls.course3 = Course.objects.create(
            course_code="ENR103", title="Enrollment 3", units=3
        )
        cls.outside_course = Course.objects.create(
            course_code="OUT101", title="Outside Curriculum", units=3
        )
        CoursePrerequisite.objects.create(
            course=cls.course3, prerequisite_course=cls.course1
        )
        for course in (cls.course1, cls.course2, cls.course3):
            CurriculumCourse.objects.create(
                curriculum=cls.curriculum,
                course=course,
                year_level=1,
                recommended_semester=1,
                course_category=CurriculumCourse.Category.CORE,
            )

        cls.term_past = AcademicTerm.objects.create(
            academic_year="2025-2026",
            semester_number=2,
            start_date="2026-01-05",
            end_date="2026-05-20",
            enrollment_open=False,
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
        cls.term_closed = AcademicTerm.objects.create(
            academic_year="2027-2028",
            semester_number=1,
            start_date="2027-08-01",
            end_date="2027-12-15",
            enrollment_open=False,
        )

        cls.instructor_user = User.objects.create_user(
            username="enr_instructor",
            password="pass12345",
            role=User.Role.INSTRUCTOR,
        )
        cls.instructor = Instructor.objects.create(
            user=cls.instructor_user, employee_number="ENR-EMP-1"
        )
        cls.other_instructor_user = User.objects.create_user(
            username="enr_instructor_2",
            password="pass12345",
            role=User.Role.INSTRUCTOR,
        )
        cls.other_instructor = Instructor.objects.create(
            user=cls.other_instructor_user, employee_number="ENR-EMP-2"
        )

        def make_section(course, term, code, day=None, start=None, end=None, **extra):
            return Section.objects.create(
                course=course,
                term=term,
                instructor=extra.pop("instructor", cls.instructor),
                section_code=code,
                capacity=extra.pop("capacity", 30),
                room_code=extra.pop("room_code", "R1"),
                day_of_week=day,
                start_time=start,
                end_time=end,
                **extra,
            )

        cls.s1 = make_section(
            cls.course1, cls.term1, "A1",
            day=Section.DayOfWeek.MONDAY, start=time(8, 0), end=time(9, 0),
        )
        cls.s1_other = make_section(
            cls.course1, cls.term1, "A2",
            day=Section.DayOfWeek.WEDNESDAY, start=time(8, 0), end=time(9, 0),
        )
        cls.s2 = make_section(
            cls.course2, cls.term1, "B1",
            day=Section.DayOfWeek.TUESDAY, start=time(9, 0), end=time(10, 0),
            instructor=cls.other_instructor,
        )
        cls.s_conflict = make_section(
            cls.course2, cls.term1, "B2",
            day=Section.DayOfWeek.MONDAY, start=time(8, 30), end=time(9, 30),
            instructor=cls.other_instructor,
        )
        cls.s_back_to_back = make_section(
            cls.course2, cls.term1, "B3",
            day=Section.DayOfWeek.MONDAY, start=time(9, 0), end=time(10, 0),
            instructor=cls.other_instructor,
        )
        cls.s_closed = make_section(
            cls.course2, cls.term1, "B4",
            day=Section.DayOfWeek.THURSDAY, start=time(8, 0), end=time(9, 0),
            instructor=cls.other_instructor, status=Section.Status.CLOSED,
        )
        cls.s_tba = make_section(cls.course2, cls.term1, "B5")
        cls.s_capacity = make_section(
            cls.course2, cls.term1, "B7",
            day=Section.DayOfWeek.FRIDAY, start=time(8, 0), end=time(9, 0),
            instructor=cls.other_instructor, capacity=1,
        )
        cls.s_prereq = make_section(
            cls.course3, cls.term1, "C2",
            day=Section.DayOfWeek.FRIDAY, start=time(10, 0), end=time(11, 0),
        )
        cls.s_outside = make_section(
            cls.outside_course, cls.term1, "D1",
            day=Section.DayOfWeek.SATURDAY, start=time(8, 0), end=time(9, 0),
        )
        cls.s_term2 = make_section(
            cls.course1, cls.term2, "E1",
            day=Section.DayOfWeek.MONDAY, start=time(8, 0), end=time(9, 0),
        )
        cls.s_cancelled = make_section(
            cls.course2, cls.term1, "B6",
            day=Section.DayOfWeek.FRIDAY, start=time(13, 0), end=time(14, 0),
            instructor=cls.other_instructor, status=Section.Status.CANCELLED,
        )
        cls.s_past_c1 = make_section(
            cls.course1, cls.term_past, "P1",
            day=Section.DayOfWeek.MONDAY, start=time(8, 0), end=time(9, 0),
        )

        cls.registrar = User.objects.create_user(
            username="enr_registrar",
            password="pass12345",
            role=User.Role.REGISTRAR,
        )
        cls.administrator = User.objects.create_user(
            username="enr_administrator",
            password="pass12345",
            role=User.Role.ADMINISTRATOR,
            is_staff=True,
        )
        cls.cashier = User.objects.create_user(
            username="enr_cashier",
            password="pass12345",
            role=User.Role.CASHIER,
        )
        cls.inactive_registrar = User.objects.create_user(
            username="enr_inactive_registrar",
            password="pass12345",
            role=User.Role.REGISTRAR,
            is_active=False,
        )
        cls.student_user = User.objects.create_user(
            username="enr_student",
            password="pass12345",
            role=User.Role.STUDENT,
            first_name="Main",
            last_name="Student",
        )
        cls.student = Student.objects.create(
            user=cls.student_user,
            student_number="ENR-2026-001",
            curriculum=cls.curriculum,
            year_level=1,
        )
        cls.student2_user = User.objects.create_user(
            username="enr_student_2",
            password="pass12345",
            role=User.Role.STUDENT,
            first_name="Other",
            last_name="Student",
        )
        cls.student2 = Student.objects.create(
            user=cls.student2_user,
            student_number="ENR-2026-002",
            curriculum=cls.curriculum,
            year_level=1,
        )
        cls.inactive_student_user = User.objects.create_user(
            username="enr_inactive_student",
            password="pass12345",
            role=User.Role.STUDENT,
            is_active=False,
        )
        cls.inactive_student = Student.objects.create(
            user=cls.inactive_student_user,
            student_number="ENR-2026-003",
            curriculum=cls.curriculum,
            year_level=1,
        )

    def make_enrollment(self, student=None, term=None, status=None):
        return Enrollment.objects.create(
            student=student or self.student,
            term=term or self.term1,
            status=status or Enrollment.Status.DRAFT,
        )

    def make_detail(self, enrollment, section, status=EnrollmentDetail.Status.ENROLLED, **extra):
        return EnrollmentDetail.objects.create(
            enrollment=enrollment,
            section=section,
            status=status,
            **extra,
        )

    def add_passed_result(
        self,
        *,
        student=None,
        section=None,
        term=None,
        detail_status=EnrollmentDetail.Status.COMPLETED,
        result_status=EnrollmentDetail.ResultStatus.PASSED,
        enrollment_status=Enrollment.Status.CONFIRMED,
        final_grade=None,
    ):
        student = student or self.student
        section = section or self.s_past_c1
        term = term or self.term_past
        enrollment = Enrollment.objects.create(
            student=student, term=term, status=enrollment_status
        )
        return EnrollmentDetail.objects.create(
            enrollment=enrollment,
            section=section,
            status=detail_status,
            result_status=result_status,
            final_grade=final_grade,
        )

    def enrollment_payload(self, **overrides):
        data = {
            "student": self.student.pk,
            "term": self.term1.pk,
        }
        data.update(overrides)
        return data


class EnrollmentAuthorizationTests(EnrollmentTestBase):
    def setUp(self):
        self.enrollment = self.make_enrollment()
        self.detail = self.make_detail(self.enrollment, self.s1)

    def test_registrar_can_access_enrollment_screens(self):
        self.client.force_login(self.registrar)
        urls = [
            reverse("enrollment:enrollment_list"),
            reverse("enrollment:enrollment_create"),
            reverse("enrollment:enrollment_detail", args=[self.enrollment.pk]),
            reverse("enrollment:enrollment_add_section", args=[self.enrollment.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(
            reverse("enrollment:enrollment_confirm", args=[self.enrollment.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.CONFIRMED)

    def test_administrator_has_read_only_access(self):
        self.client.force_login(self.administrator)
        self.assertEqual(
            self.client.get(reverse("enrollment:enrollment_list")).status_code, 200
        )
        self.assertEqual(
            self.client.get(
                reverse("enrollment:enrollment_detail", args=[self.enrollment.pk])
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("enrollment:enrollment_create")).status_code, 403
        )
        self.assertEqual(
            self.client.get(
                reverse("enrollment:enrollment_add_section", args=[self.enrollment.pk])
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("enrollment:enrollment_confirm", args=[self.enrollment.pk])
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse(
                    "enrollment:enrollment_remove_section",
                    args=[self.enrollment.pk, self.detail.pk],
                )
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("enrollment:enrollment_create"),
                self.enrollment_payload(
                    student=self.student2.pk, term=self.term2.pk
                ),
            ).status_code,
            403,
        )
        self.assertFalse(
            Enrollment.objects.filter(
                student=self.student2, term=self.term2
            ).exists()
        )

    def test_other_roles_are_denied(self):
        for user in (self.cashier, self.instructor_user):
            self.client.force_login(user)
            with self.subTest(role=user.role):
                self.assertEqual(
                    self.client.get(reverse("enrollment:enrollment_list")).status_code,
                    403,
                )
                self.assertEqual(
                    self.client.get(reverse("enrollment:enrollment_create")).status_code,
                    403,
                )
                self.assertEqual(
                    self.client.get(
                        reverse(
                            "enrollment:enrollment_detail",
                            args=[self.enrollment.pk],
                        )
                    ).status_code,
                    403,
                )
                self.assertEqual(
                    self.client.get(
                        reverse(
                            "enrollment:enrollment_add_section",
                            args=[self.enrollment.pk],
                        )
                    ).status_code,
                    403,
                )
                self.assertEqual(
                    self.client.post(
                        reverse(
                            "enrollment:enrollment_confirm",
                            args=[self.enrollment.pk],
                        )
                    ).status_code,
                    403,
                )
                self.assertEqual(
                    self.client.post(
                        reverse(
                            "enrollment:enrollment_remove_section",
                            args=[self.enrollment.pk, self.detail.pk],
                        )
                    ).status_code,
                    403,
                )

    def test_anonymous_redirected_to_login_with_next(self):
        response = self.client.get(reverse("enrollment:enrollment_list"))
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
        for url in [
            reverse("enrollment:enrollment_list"),
            reverse("enrollment:enrollment_create"),
            reverse("enrollment:enrollment_detail", args=[self.enrollment.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_student_sees_only_own_enrollments(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("enrollment:my_enrollment_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.term1.__str__())
        self.assertEqual(
            self.client.get(
                reverse("enrollment:my_enrollment_detail", args=[self.enrollment.pk])
            ).status_code,
            200,
        )

        self.client.force_login(self.student2_user)
        self.assertEqual(
            self.client.get(
                reverse("enrollment:my_enrollment_detail", args=[self.enrollment.pk])
            ).status_code,
            404,
        )

    def test_active_section_count_excludes_cancelled_enrollments(self):
        self.client.force_login(self.registrar)
        self.enrollment.status = Enrollment.Status.CANCELLED
        self.enrollment.save(update_fields=["status"])

        response = self.client.get(reverse("enrollment:enrollment_list"))

        enrollment = response.context["enrollments"].get(pk=self.enrollment.pk)
        self.assertEqual(enrollment.active_section_count, 0)

    def test_student_cannot_access_registrar_enrollment_screens(self):
        self.client.force_login(self.student_user)
        self.assertEqual(
            self.client.get(reverse("enrollment:enrollment_list")).status_code, 403
        )
        self.assertEqual(
            self.client.get(reverse("enrollment:enrollment_create")).status_code, 403
        )
        self.assertEqual(
            self.client.post(
                reverse("enrollment:enrollment_confirm", args=[self.enrollment.pk])
            ).status_code,
            403,
        )

    def test_registrar_cannot_access_student_portal(self):
        self.client.force_login(self.registrar)
        self.assertEqual(
            self.client.get(reverse("enrollment:my_enrollment_list")).status_code, 403
        )
        self.assertEqual(
            self.client.get(
                reverse("enrollment:my_enrollment_detail", args=[self.enrollment.pk])
            ).status_code,
            403,
        )

    def test_student_without_profile_has_safe_empty_state(self):
        user = User.objects.create_user(
            username="enr_no_profile",
            password="pass12345",
            role=User.Role.STUDENT,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("enrollment:my_enrollment_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no enrollments")
        self.assertEqual(
            self.client.get(
                reverse("enrollment:my_enrollment_detail", args=[self.enrollment.pk])
            ).status_code,
            404,
        )


class EnrollmentCreationTests(EnrollmentTestBase):
    def setUp(self):
        self.client.force_login(self.registrar)

    def test_registrar_can_create_draft_enrollment(self):
        response = self.client.post(
            reverse("enrollment:enrollment_create"), self.enrollment_payload()
        )
        self.assertEqual(response.status_code, 302)
        enrollment = Enrollment.objects.get(student=self.student, term=self.term1)
        self.assertEqual(enrollment.status, Enrollment.Status.DRAFT)
        self.assertRedirects(
            response,
            reverse("enrollment:enrollment_detail", args=[enrollment.pk]),
        )

    def test_duplicate_student_and_term_is_rejected_readably(self):
        self.make_enrollment()
        response = self.client.post(
            reverse("enrollment:enrollment_create"), self.enrollment_payload()
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already has an enrollment")
        self.assertEqual(
            Enrollment.objects.filter(
                student=self.student, term=self.term1
            ).count(),
            1,
        )

    def test_closed_term_is_rejected(self):
        response = self.client.post(
            reverse("enrollment:enrollment_create"),
            self.enrollment_payload(
                student=self.student2.pk, term=self.term_closed.pk
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not open")
        self.assertFalse(
            Enrollment.objects.filter(
                student=self.student2, term=self.term_closed
            ).exists()
        )

    def test_inactive_student_is_rejected_by_service(self):
        with self.assertRaises(ValidationError):
            create_enrollment(
                student=self.inactive_student, term=self.term1
            )
        self.assertFalse(
            Enrollment.objects.filter(student=self.inactive_student).exists()
        )

    def test_cancelled_enrollment_blocks_replacement(self):
        self.make_enrollment(status=Enrollment.Status.CANCELLED)
        response = self.client.post(
            reverse("enrollment:enrollment_create"), self.enrollment_payload()
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already has an enrollment")


class EnrollmentAddSectionTests(EnrollmentTestBase):
    def setUp(self):
        self.client.force_login(self.registrar)
        self.enrollment = self.make_enrollment()

    def add(self, section):
        return self.client.post(
            reverse(
                "enrollment:enrollment_add_section", args=[self.enrollment.pk]
            ),
            {"section": section.pk},
        )

    def test_eligible_section_is_added(self):
        response = self.add(self.s1)
        self.assertEqual(response.status_code, 302)
        detail = EnrollmentDetail.objects.get(
            enrollment=self.enrollment, section=self.s1
        )
        self.assertEqual(detail.status, EnrollmentDetail.Status.ENROLLED)

    def test_duplicate_section_is_rejected(self):
        self.add(self.s1)
        response = self.add(self.s1)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already part of the enrollment")
        self.assertEqual(
            EnrollmentDetail.objects.filter(
                enrollment=self.enrollment, section=self.s1
            ).count(),
            1,
        )

    def test_duplicate_course_is_rejected(self):
        self.add(self.s1)
        response = self.add(self.s1_other)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "another section of this course")

    def test_wrong_term_section_is_rejected_by_service(self):
        with self.assertRaises(ValidationError):
            enroll_in_section(enrollment=self.enrollment, section=self.s_term2)
        self.assertFalse(
            EnrollmentDetail.objects.filter(
                enrollment=self.enrollment, section=self.s_term2
            ).exists()
        )

    def test_full_section_is_rejected(self):
        other_enrollment = self.make_enrollment(student=self.student2)
        enroll_in_section(enrollment=other_enrollment, section=self.s_capacity)
        response = self.add(self.s_capacity)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "reached its capacity")

    def test_non_open_section_is_rejected(self):
        response = self.add(self.s_closed)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not open for enrollment")

    def test_tba_section_is_rejected(self):
        response = self.add(self.s_tba)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "schedule is not complete")

    def test_course_outside_curriculum_is_rejected(self):
        response = self.add(self.s_outside)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not part of the student")

    def test_student_schedule_conflict_is_rejected(self):
        self.add(self.s1)
        response = self.add(self.s_conflict)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already has a section")

    def test_back_to_back_schedule_is_allowed(self):
        self.add(self.s1)
        response = self.add(self.s_back_to_back)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            EnrollmentDetail.objects.filter(
                enrollment=self.enrollment, section=self.s_back_to_back
            ).exists()
        )

    def test_enrollment_open_is_enforced_when_adding(self):
        self.term1.enrollment_open = False
        self.term1.save(update_fields=["enrollment_open"])
        response = self.add(self.s1)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not open")
        self.assertFalse(
            EnrollmentDetail.objects.filter(
                enrollment=self.enrollment, section=self.s1
            ).exists()
        )

    def test_confirmed_enrollment_cannot_receive_sections(self):
        self.add(self.s1)
        confirm_enrollment(enrollment=self.enrollment)
        response = self.add(self.s2)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "draft enrollment")
        self.assertFalse(
            EnrollmentDetail.objects.filter(
                enrollment=self.enrollment, section=self.s2
            ).exists()
        )

    def test_integrity_error_is_handled_after_rollback(self):
        with patch.object(
            EnrollmentDetail, "save", side_effect=IntegrityError("duplicate")
        ):
            response = self.add(self.s1)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        self.assertFalse(
            EnrollmentDetail.objects.filter(
                enrollment=self.enrollment, section=self.s1
            ).exists()
        )
        response = self.add(self.s1)
        self.assertEqual(response.status_code, 302)


class PrerequisiteTests(EnrollmentTestBase):
    def setUp(self):
        self.enrollment = self.make_enrollment()

    def test_missing_prerequisite_is_reported(self):
        with self.assertRaises(ValidationError):
            enroll_in_section(
                enrollment=self.enrollment, section=self.s_prereq
            )
        self.assertEqual(
            [
                course.course_code
                for course in missing_prerequisites(
                    self.student, self.course3, term=self.term1
                )
            ],
            ["ENR101"],
        )

    def test_completed_and_passed_satisfies_prerequisite(self):
        self.add_passed_result()
        detail = enroll_in_section(
            enrollment=self.enrollment, section=self.s_prereq
        )
        self.assertEqual(detail.section, self.s_prereq)

    def test_completed_with_failed_result_does_not_satisfy(self):
        self.add_passed_result(
            result_status=EnrollmentDetail.ResultStatus.FAILED,
            final_grade=Decimal("4.00"),
        )
        with self.assertRaises(ValidationError):
            enroll_in_section(
                enrollment=self.enrollment, section=self.s_prereq
            )

    def test_numeric_grade_without_passed_result_does_not_satisfy(self):
        self.add_passed_result(
            result_status=EnrollmentDetail.ResultStatus.INCOMPLETE,
            final_grade=Decimal("1.00"),
        )
        with self.assertRaises(ValidationError):
            enroll_in_section(
                enrollment=self.enrollment, section=self.s_prereq
            )

    def test_enrolled_with_passed_result_does_not_satisfy(self):
        self.add_passed_result(
            detail_status=EnrollmentDetail.Status.ENROLLED
        )
        with self.assertRaises(ValidationError):
            enroll_in_section(
                enrollment=self.enrollment, section=self.s_prereq
            )

    def test_same_term_result_does_not_satisfy(self):
        self.make_detail(
            self.enrollment,
            self.s1,
            status=EnrollmentDetail.Status.COMPLETED,
            result_status=EnrollmentDetail.ResultStatus.PASSED,
        )
        with self.assertRaises(ValidationError):
            enroll_in_section(
                enrollment=self.enrollment, section=self.s_prereq
            )

    def test_cancelled_enrollment_result_does_not_satisfy(self):
        self.add_passed_result(
            enrollment_status=Enrollment.Status.CANCELLED
        )
        with self.assertRaises(ValidationError):
            enroll_in_section(
                enrollment=self.enrollment, section=self.s_prereq
            )


class EnrollmentConfirmationTests(EnrollmentTestBase):
    def setUp(self):
        self.client.force_login(self.registrar)
        self.enrollment = self.make_enrollment()

    def test_confirm_draft_with_section(self):
        detail = self.make_detail(self.enrollment, self.s1)
        response = self.client.post(
            reverse("enrollment:enrollment_confirm", args=[self.enrollment.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.CONFIRMED)
        detail.refresh_from_db()
        self.assertEqual(detail.status, EnrollmentDetail.Status.ENROLLED)

    def test_empty_enrollment_cannot_be_confirmed(self):
        response = self.client.post(
            reverse("enrollment:enrollment_confirm", args=[self.enrollment.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.DRAFT)

    def test_enrollment_with_cancelled_section_cannot_be_confirmed(self):
        self.make_detail(self.enrollment, self.s_cancelled)
        with self.assertRaises(ValidationError):
            confirm_enrollment(enrollment=self.enrollment)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.DRAFT)

    def test_confirmation_allowed_after_term_closes(self):
        self.make_detail(self.enrollment, self.s1)
        self.term1.enrollment_open = False
        self.term1.save(update_fields=["enrollment_open"])
        confirm_enrollment(enrollment=self.enrollment)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.CONFIRMED)

    def test_confirmed_enrollment_cannot_be_confirmed_again(self):
        self.make_detail(self.enrollment, self.s1)
        confirm_enrollment(enrollment=self.enrollment)
        with self.assertRaises(ValidationError):
            confirm_enrollment(enrollment=self.enrollment)

    def test_confirm_endpoint_rejects_get(self):
        response = self.client.get(
            reverse("enrollment:enrollment_confirm", args=[self.enrollment.pk])
        )
        self.assertEqual(response.status_code, 405)

    def test_add_section_get_rejected_for_confirmed_enrollment(self):
        self.make_detail(self.enrollment, self.s1)
        confirm_enrollment(enrollment=self.enrollment)

        response = self.client.get(
            reverse(
                "enrollment:enrollment_add_section", args=[self.enrollment.pk]
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "enrollment:enrollment_detail", args=[self.enrollment.pk]
            ),
        )

    def test_confirm_button_available_with_active_detail(self):
        self.make_detail(self.enrollment, self.s1)

        response = self.client.get(
            reverse(
                "enrollment:enrollment_detail", args=[self.enrollment.pk]
            )
        )

        self.assertContains(response, "Confirm Enrollment")

    def test_confirm_button_hidden_when_only_dropped_details(self):
        detail = self.make_detail(self.enrollment, self.s1)
        drop_enrollment_detail(detail=detail)

        response = self.client.get(
            reverse(
                "enrollment:enrollment_detail", args=[self.enrollment.pk]
            )
        )

        self.assertNotContains(response, "Confirm Enrollment")


class ConfirmationRevalidationTests(EnrollmentTestBase):
    def setUp(self):
        self.enrollment = self.make_enrollment()

    def test_confirmation_rejects_section_from_another_term(self):
        self.make_detail(self.enrollment, self.s_term2)

        with self.assertRaisesMessage(
            ValidationError, "different academic term"
        ):
            confirm_enrollment(enrollment=self.enrollment)

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.DRAFT)

    def test_confirmation_rejects_incomplete_schedule(self):
        self.make_detail(self.enrollment, self.s_tba)

        with self.assertRaisesMessage(ValidationError, "complete schedule"):
            confirm_enrollment(enrollment=self.enrollment)

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.DRAFT)

    def test_confirmation_rejects_over_capacity_section(self):
        self.make_detail(self.enrollment, self.s_capacity)
        other_enrollment = self.make_enrollment(student=self.student2)
        self.make_detail(other_enrollment, self.s_capacity)

        with self.assertRaisesMessage(ValidationError, "capacity"):
            confirm_enrollment(enrollment=self.enrollment)

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.DRAFT)

    def test_confirmation_allows_closed_section(self):
        self.make_detail(self.enrollment, self.s_closed)

        confirm_enrollment(enrollment=self.enrollment)

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.CONFIRMED)

    def test_dropped_details_do_not_count_as_active(self):
        detail = self.make_detail(self.enrollment, self.s1)
        drop_enrollment_detail(detail=detail)

        with self.assertRaisesMessage(ValidationError, "at least one section"):
            confirm_enrollment(enrollment=self.enrollment)

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.DRAFT)


class SectionRemovalTests(EnrollmentTestBase):
    def setUp(self):
        self.client.force_login(self.registrar)
        self.enrollment = self.make_enrollment()
        self.detail = self.make_detail(self.enrollment, self.s1)

    def remove(self, detail, **data):
        return self.client.post(
            reverse(
                "enrollment:enrollment_remove_section",
                args=[self.enrollment.pk, detail.pk],
            ),
            data,
        )

    def test_remove_endpoint_rejects_get(self):
        response = self.client.get(
            reverse(
                "enrollment:enrollment_remove_section",
                args=[self.enrollment.pk, self.detail.pk],
            )
        )
        self.assertEqual(response.status_code, 405)

    def test_removing_section_marks_detail_dropped(self):
        response = self.remove(self.detail)
        self.assertEqual(response.status_code, 302)
        self.detail.refresh_from_db()
        self.assertEqual(self.detail.status, EnrollmentDetail.Status.DROPPED)
        self.assertEqual(
            self.detail.result_status, EnrollmentDetail.ResultStatus.DROPPED
        )
        self.assertIsNotNone(self.detail.recorded_at)

    def test_withdrawn_result_status_is_recorded(self):
        response = self.remove(self.detail, withdrawn="1")
        self.assertEqual(response.status_code, 302)
        self.detail.refresh_from_db()
        self.assertEqual(self.detail.status, EnrollmentDetail.Status.DROPPED)
        self.assertEqual(
            self.detail.result_status, EnrollmentDetail.ResultStatus.WITHDRAWN
        )
        self.assertIsNotNone(self.detail.recorded_at)

    def test_removal_frees_capacity(self):
        other_enrollment = self.make_enrollment(student=self.student2)
        enroll_in_section(
            enrollment=other_enrollment, section=self.s_capacity
        )
        with self.assertRaises(ValidationError):
            enroll_in_section(
                enrollment=self.enrollment, section=self.s_capacity
            )
        detail = EnrollmentDetail.objects.get(
            enrollment=other_enrollment, section=self.s_capacity
        )
        drop_enrollment_detail(detail=detail)
        detail = enroll_in_section(
            enrollment=self.enrollment, section=self.s_capacity
        )
        self.assertEqual(detail.status, EnrollmentDetail.Status.ENROLLED)

    def test_confirmed_enrollment_cannot_remove_sections(self):
        confirm_enrollment(enrollment=self.enrollment)
        response = self.remove(self.detail)
        self.assertEqual(response.status_code, 302)
        self.detail.refresh_from_db()
        self.assertEqual(self.detail.status, EnrollmentDetail.Status.ENROLLED)

    def test_non_enrolled_detail_cannot_be_removed(self):
        self.detail.status = EnrollmentDetail.Status.DROPPED
        self.detail.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            drop_enrollment_detail(detail=self.detail)


class EnrollmentIntegrityErrorTests(EnrollmentTestBase):
    def setUp(self):
        self.client.force_login(self.registrar)

    def test_create_enrollment_integrity_error_is_handled(self):
        with patch.object(Enrollment, "save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(
                reverse("enrollment:enrollment_create"),
                self.enrollment_payload(),
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        self.assertFalse(
            Enrollment.objects.filter(
                student=self.student, term=self.term1
            ).exists()
        )
        response = self.client.post(
            reverse("enrollment:enrollment_create"), self.enrollment_payload()
        )
        self.assertEqual(response.status_code, 302)

    def test_add_section_integrity_error_is_handled(self):
        enrollment = self.make_enrollment()
        with patch.object(
            EnrollmentDetail, "save", side_effect=IntegrityError("duplicate")
        ):
            response = self.client.post(
                reverse(
                    "enrollment:enrollment_add_section", args=[enrollment.pk]
                ),
                {"section": self.s1.pk},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        self.assertFalse(
            EnrollmentDetail.objects.filter(
                enrollment=enrollment, section=self.s1
            ).exists()
        )
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, Enrollment.Status.DRAFT)

    def test_integrity_error_response_does_not_leak_database_details(self):
        enrollment = self.make_enrollment()
        with patch.object(
            EnrollmentDetail, "save", side_effect=IntegrityError("duplicate")
        ):
            response = self.client.post(
                reverse(
                    "enrollment:enrollment_add_section", args=[enrollment.pk]
                ),
                {"section": self.s1.pk},
            )
        content = response.content.decode()
        self.assertNotIn("IntegrityError", content)
        self.assertNotIn("Duplicate entry", content)
        self.assertNotIn("INSERT INTO", content)
        self.assertNotIn("Traceback", content)
