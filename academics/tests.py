from datetime import date
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
    CoursePrerequisite,
    Curriculum,
    CurriculumCourse,
    Program,
)


class AcademicScreenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.college = College.objects.create(
            college_code="ENG", name="College of Engineering"
        )
        cls.program = Program.objects.create(
            college=cls.college, program_code="BSCE", name="Civil Engineering"
        )
        cls.curriculum = Curriculum.objects.create(
            program=cls.program,
            curriculum_code="BSCE-2024",
            effective_year=2024,
        )
        cls.course1 = Course.objects.create(
            course_code="MATH1", title="Mathematics 1", units=3
        )
        cls.course2 = Course.objects.create(
            course_code="MATH2", title="Mathematics 2", units=3
        )
        cls.term = AcademicTerm.objects.create(
            academic_year="2024-2025",
            semester_number=1,
            start_date=date(2024, 8, 1),
            end_date=date(2024, 12, 15),
        )
        cls.curriculum_course = CurriculumCourse.objects.create(
            curriculum=cls.curriculum,
            course=cls.course1,
            year_level=1,
            recommended_semester=1,
            course_category=CurriculumCourse.Category.CORE,
        )
        cls.prerequisite = CoursePrerequisite.objects.create(
            course=cls.course2, prerequisite_course=cls.course1
        )

        cls.registrar = User.objects.create_user(
            username="acad_reg",
            password="pass12345",
            role=User.Role.REGISTRAR,
        )
        cls.administrator = User.objects.create_user(
            username="acad_admin",
            password="pass12345",
            role=User.Role.ADMINISTRATOR,
            is_staff=True,
        )
        cls.cashier = User.objects.create_user(
            username="acad_cash",
            password="pass12345",
            role=User.Role.CASHIER,
        )
        cls.inactive_registrar = User.objects.create_user(
            username="acad_inactive_reg",
            password="pass12345",
            role=User.Role.REGISTRAR,
            is_active=False,
        )

    def list_urls(self):
        return [
            reverse("academics:college_list"),
            reverse("academics:program_list"),
            reverse("academics:curriculum_list"),
            reverse("academics:course_list"),
            reverse("academics:curriculum_course_list"),
            reverse("academics:course_prerequisite_list"),
            reverse("academics:academic_term_list"),
        ]

    def detail_urls(self):
        return [
            reverse("academics:college_detail", args=[self.college.pk]),
            reverse("academics:program_detail", args=[self.program.pk]),
            reverse("academics:curriculum_detail", args=[self.curriculum.pk]),
            reverse("academics:course_detail", args=[self.course1.pk]),
            reverse(
                "academics:curriculum_course_detail",
                args=[self.curriculum_course.pk],
            ),
            reverse(
                "academics:course_prerequisite_detail",
                args=[self.prerequisite.pk],
            ),
            reverse("academics:academic_term_detail", args=[self.term.pk]),
        ]

    def test_registrar_can_list_all_master_data(self):
        self.client.force_login(self.registrar)
        for url in self.list_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_registrar_can_view_all_details(self):
        self.client.force_login(self.registrar)
        for url in self.detail_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_registrar_can_open_all_create_forms(self):
        self.client.force_login(self.registrar)
        urls = [
            reverse("academics:college_create"),
            reverse("academics:program_create"),
            reverse("academics:curriculum_create"),
            reverse("academics:course_create"),
            reverse("academics:curriculum_course_create"),
            reverse("academics:course_prerequisite_create"),
            reverse("academics:academic_term_create"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_registrar_can_open_all_update_forms(self):
        self.client.force_login(self.registrar)
        urls = [
            reverse("academics:college_update", args=[self.college.pk]),
            reverse("academics:program_update", args=[self.program.pk]),
            reverse("academics:curriculum_update", args=[self.curriculum.pk]),
            reverse("academics:course_update", args=[self.course1.pk]),
            reverse(
                "academics:curriculum_course_update",
                args=[self.curriculum_course.pk],
            ),
            reverse(
                "academics:course_prerequisite_update",
                args=[self.prerequisite.pk],
            ),
            reverse("academics:academic_term_update", args=[self.term.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_registrar_can_create_all_master_data(self):
        self.client.force_login(self.registrar)
        cases = [
            (
                reverse("academics:college_create"),
                {"college_code": "NEW-C", "name": "New College", "is_active": "on"},
                College,
                {"college_code": "NEW-C"},
            ),
            (
                reverse("academics:program_create"),
                {
                    "college": self.college.pk,
                    "program_code": "NEW-P",
                    "name": "New Program",
                    "description": "",
                    "is_active": "on",
                },
                Program,
                {"program_code": "NEW-P"},
            ),
            (
                reverse("academics:curriculum_create"),
                {
                    "program": self.program.pk,
                    "curriculum_code": "NEW-CUR",
                    "effective_year": 2025,
                    "is_active": "on",
                },
                Curriculum,
                {"curriculum_code": "NEW-CUR"},
            ),
            (
                reverse("academics:course_create"),
                {
                    "course_code": "NEW-CRS",
                    "title": "New Course",
                    "description": "",
                    "units": "3.0",
                    "is_active": "on",
                },
                Course,
                {"course_code": "NEW-CRS"},
            ),
            (
                reverse("academics:curriculum_course_create"),
                {
                    "curriculum": self.curriculum.pk,
                    "course": self.course2.pk,
                    "year_level": 2,
                    "recommended_semester": 2,
                    "course_category": CurriculumCourse.Category.MAJOR,
                },
                CurriculumCourse,
                {"curriculum": self.curriculum, "course": self.course2},
            ),
            (
                reverse("academics:course_prerequisite_create"),
                {
                    "course": self.course1.pk,
                    "prerequisite_course": self.course2.pk,
                },
                CoursePrerequisite,
                {"course": self.course1, "prerequisite_course": self.course2},
            ),
            (
                reverse("academics:academic_term_create"),
                {
                    "academic_year": "2025-2026",
                    "semester_number": 2,
                    "start_date": "2026-01-05",
                    "end_date": "2026-05-20",
                    "enrollment_open": "on",
                },
                AcademicTerm,
                {"academic_year": "2025-2026", "semester_number": 2},
            ),
        ]
        for url, data, model, lookup in cases:
            with self.subTest(url=url):
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(model.objects.filter(**lookup).exists())

    def test_registrar_can_update_all_master_data(self):
        self.client.force_login(self.registrar)
        college = College.objects.create(college_code="UPD-C", name="Old College")
        program = Program.objects.create(
            college=self.college, program_code="UPD-P", name="Old Program"
        )
        curriculum = Curriculum.objects.create(
            program=self.program,
            curriculum_code="UPD-CUR",
            effective_year=2024,
        )
        course = Course.objects.create(
            course_code="UPD-CRS", title="Old Course", units=3
        )
        alternate_course = Course.objects.create(
            course_code="ALT-CRS", title="Alternate Course", units=3
        )
        curriculum_course = CurriculumCourse.objects.create(
            curriculum=self.curriculum,
            course=course,
            year_level=1,
            recommended_semester=1,
            course_category=CurriculumCourse.Category.CORE,
        )
        prerequisite = CoursePrerequisite.objects.create(
            course=self.course2, prerequisite_course=course
        )
        term = AcademicTerm.objects.create(
            academic_year="2027-2028",
            semester_number=1,
            start_date=date(2027, 8, 1),
            end_date=date(2027, 12, 15),
        )

        cases = [
            (
                reverse("academics:college_update", args=[college.pk]),
                {"college_code": "UPD-C", "name": "Updated College", "is_active": "on"},
                college,
                "name",
                "Updated College",
            ),
            (
                reverse("academics:program_update", args=[program.pk]),
                {
                    "college": self.college.pk,
                    "program_code": "UPD-P",
                    "name": "Updated Program",
                    "description": "",
                    "is_active": "on",
                },
                program,
                "name",
                "Updated Program",
            ),
            (
                reverse("academics:curriculum_update", args=[curriculum.pk]),
                {
                    "program": self.program.pk,
                    "curriculum_code": "UPD-CUR",
                    "effective_year": 2028,
                    "is_active": "on",
                },
                curriculum,
                "effective_year",
                2028,
            ),
            (
                reverse("academics:course_update", args=[course.pk]),
                {
                    "course_code": "UPD-CRS",
                    "title": "Updated Course",
                    "description": "",
                    "units": "4.0",
                    "is_active": "on",
                },
                course,
                "title",
                "Updated Course",
            ),
            (
                reverse(
                    "academics:curriculum_course_update",
                    args=[curriculum_course.pk],
                ),
                {
                    "curriculum": self.curriculum.pk,
                    "course": course.pk,
                    "year_level": 3,
                    "recommended_semester": 1,
                    "course_category": CurriculumCourse.Category.CORE,
                },
                curriculum_course,
                "year_level",
                3,
            ),
            (
                reverse(
                    "academics:course_prerequisite_update",
                    args=[prerequisite.pk],
                ),
                {
                    "course": self.course2.pk,
                    "prerequisite_course": alternate_course.pk,
                },
                prerequisite,
                "prerequisite_course_id",
                alternate_course.pk,
            ),
            (
                reverse("academics:academic_term_update", args=[term.pk]),
                {
                    "academic_year": "2027-2028",
                    "semester_number": 2,
                    "start_date": "2027-08-01",
                    "end_date": "2027-12-15",
                    "enrollment_open": "on",
                },
                term,
                "semester_number",
                2,
            ),
        ]
        for url, data, obj, field, expected in cases:
            with self.subTest(url=url):
                response = self.client.post(url, data)
                self.assertEqual(response.status_code, 302)
                obj.refresh_from_db()
                self.assertEqual(getattr(obj, field), expected)

    def test_administrator_can_read_but_not_write(self):
        self.client.force_login(self.administrator)
        for url in self.list_urls() + self.detail_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        write_urls = [
            reverse("academics:college_create"),
            reverse("academics:program_create"),
            reverse("academics:curriculum_create"),
            reverse("academics:course_create"),
            reverse("academics:curriculum_course_create"),
            reverse("academics:course_prerequisite_create"),
            reverse("academics:academic_term_create"),
            reverse("academics:college_update", args=[self.college.pk]),
        ]
        for url in write_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        response = self.client.post(
            reverse("academics:college_create"),
            {"college_code": "ADMIN-C", "name": "Denied", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(College.objects.filter(college_code="ADMIN-C").exists())

    def test_other_active_roles_are_denied(self):
        self.client.force_login(self.cashier)
        self.assertEqual(self.client.get(reverse("academics:college_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("academics:college_create")).status_code, 403)

    def test_anonymous_redirected_to_login_with_next(self):
        response = self.client.get(reverse("academics:college_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        self.assertIn("next=", response.url)

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.AllowAllUsersModelBackend",
        ]
    )
    def test_inactive_registrar_denied_every_academic_screen(self):
        self.client.force_login(self.inactive_registrar)
        urls = [
            reverse("academics:college_list"),
            reverse("academics:college_create"),
            reverse("academics:college_detail", args=[self.college.pk]),
            reverse("academics:college_update", args=[self.college.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.AllowAllUsersModelBackend",
        ]
    )
    def test_inactive_administrator_denied_detail(self):
        self.client.force_login(self.inactive_registrar)
        self.assertEqual(
            self.client.get(
                reverse("academics:program_detail", args=[self.program.pk])
            ).status_code,
            403,
        )

    def test_duplicate_college_code_is_rejected_readably(self):
        self.client.force_login(self.registrar)
        response = self.client.post(
            reverse("academics:college_create"),
            {"college_code": "ENG", "name": "Duplicate", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertFalse(College.objects.filter(name="Duplicate").exists())

    def test_term_date_range_is_validated(self):
        self.client.force_login(self.registrar)
        response = self.client.post(
            reverse("academics:academic_term_create"),
            {
                "academic_year": "2028-2029",
                "semester_number": 1,
                "start_date": "2028-12-01",
                "end_date": "2028-08-01",
                "enrollment_open": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "End date must be on or after the start date.")
        self.assertFalse(AcademicTerm.objects.filter(academic_year="2028-2029").exists())

    def test_self_prerequisite_is_rejected(self):
        self.client.force_login(self.registrar)
        response = self.client.post(
            reverse("academics:course_prerequisite_create"),
            {"course": self.course1.pk, "prerequisite_course": self.course1.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot be its own prerequisite")

    def test_zero_units_is_rejected(self):
        self.client.force_login(self.registrar)
        response = self.client.post(
            reverse("academics:course_create"),
            {
                "course_code": "ZERO-CRS",
                "title": "Zero Units",
                "description": "",
                "units": "0",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Units must be greater than zero.")

    def test_academic_year_has_no_format_regex(self):
        self.client.force_login(self.registrar)
        response = self.client.post(
            reverse("academics:academic_term_create"),
            {
                "academic_year": "2024-25",
                "semester_number": 2,
                "start_date": "2024-01-05",
                "end_date": "2024-05-20",
                "enrollment_open": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            AcademicTerm.objects.filter(
                academic_year="2024-25", semester_number=2
            ).exists()
        )


class AcademicIntegrityErrorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.college = College.objects.create(
            college_code="INT-ENG", name="Integrity College"
        )
        cls.program = Program.objects.create(
            college=cls.college,
            program_code="INT-P",
            name="Integrity Program",
        )
        cls.registrar = User.objects.create_user(
            username="int_reg",
            password="pass12345",
            role=User.Role.REGISTRAR,
        )

    def setUp(self):
        self.client.force_login(self.registrar)

    def test_college_create_integrity_error_is_handled(self):
        with patch.object(College, "save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(
                reverse("academics:college_create"),
                {"college_code": "INT-NEW", "name": "New", "is_active": "on"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        self.assertFalse(College.objects.filter(college_code="INT-NEW").exists())
        College.objects.create(college_code="AFTER-C", name="After Error")
        self.assertTrue(College.objects.filter(college_code="AFTER-C").exists())

    def test_college_update_integrity_error_is_handled(self):
        with patch.object(College, "save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(
                reverse("academics:college_update", args=[self.college.pk]),
                {
                    "college_code": "INT-ENG",
                    "name": "Changed Name",
                    "is_active": "on",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        self.college.refresh_from_db()
        self.assertEqual(self.college.name, "Integrity College")

    def test_program_create_integrity_error_is_handled(self):
        with patch.object(Program, "save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(
                reverse("academics:program_create"),
                {
                    "college": self.college.pk,
                    "program_code": "INT-NEW-P",
                    "name": "New Program",
                    "description": "",
                    "is_active": "on",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        self.assertFalse(Program.objects.filter(program_code="INT-NEW-P").exists())

    def test_course_create_integrity_error_is_handled(self):
        with patch.object(Course, "save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(
                reverse("academics:course_create"),
                {
                    "course_code": "INT-NEW-CRS",
                    "title": "New Course",
                    "description": "",
                    "units": "3.0",
                    "is_active": "on",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        self.assertFalse(Course.objects.filter(course_code="INT-NEW-CRS").exists())

    def test_academic_term_create_integrity_error_is_handled(self):
        with patch.object(
            AcademicTerm, "save", side_effect=IntegrityError("duplicate")
        ):
            response = self.client.post(
                reverse("academics:academic_term_create"),
                {
                    "academic_year": "2030-2031",
                    "semester_number": 1,
                    "start_date": "2030-08-01",
                    "end_date": "2030-12-15",
                    "enrollment_open": "on",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        self.assertFalse(
            AcademicTerm.objects.filter(academic_year="2030-2031").exists()
        )
        AcademicTerm.objects.create(
            academic_year="2031-2032",
            semester_number=1,
            start_date=date(2031, 8, 1),
            end_date=date(2031, 12, 15),
        )

    def test_integrity_error_response_does_not_leak_database_details(self):
        with patch.object(College, "save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(
                reverse("academics:college_create"),
                {"college_code": "INT-LEAK", "name": "Leak", "is_active": "on"},
            )
        content = response.content.decode()
        self.assertNotIn("IntegrityError", content)
        self.assertNotIn("Duplicate entry", content)
        self.assertNotIn("INSERT INTO", content)
        self.assertNotIn("Traceback", content)
