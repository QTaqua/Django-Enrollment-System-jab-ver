"""Milestone C tests: enrolled / semester / collection reports + CSV exports
and server-side report permissions."""

from datetime import time, datetime, timezone as dt_tz
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.report_views import _csv_safe
from academics.models import (
    AcademicTerm, College, Course, Curriculum, CurriculumCourse, Program, Student,
)
from enrollment.models import Enrollment, EnrollmentDetail
from scheduling.models import Section
from finance.models import Assessment, Payment, ScholarshipAward

D = Decimal


class ReportTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.college = College.objects.create(college_code="RPT-C", name="Reports College")
        cls.program = Program.objects.create(college=cls.college, program_code="RPT-BS", name="Reports Program")
        cls.curriculum = Curriculum.objects.create(program=cls.program, curriculum_code="RPT-CUR", effective_year=2026)
        cls.term1 = AcademicTerm.objects.create(academic_year="2026-2027", semester_number=1,
                                                 start_date="2026-08-01", end_date="2026-12-15", enrollment_open=True)
        cls.term2 = AcademicTerm.objects.create(academic_year="2025-2026", semester_number=2,
                                                 start_date="2026-01-05", end_date="2026-05-15")
        cls.course1 = Course.objects.create(course_code="RPT101", title="Course One", units=D("3.0"))
        cls.course2 = Course.objects.create(course_code="RPT102", title="Course Two", units=D("3.0"))
        for c in (cls.course1, cls.course2):
            CurriculumCourse.objects.create(curriculum=cls.curriculum, course=c, year_level=1,
                                            recommended_semester=1, course_category="CORE")
        cls.sec1 = Section.objects.create(course=cls.course1, term=cls.term1, section_code="S1",
                                          capacity=40, day_of_week=0, start_time=time(8, 0), end_time=time(9, 30))
        cls.sec2 = Section.objects.create(course=cls.course2, term=cls.term1, section_code="S2",
                                          capacity=40, day_of_week=1, start_time=time(8, 0), end_time=time(9, 30))

        def mkstudent(username, number, year):
            u = User.objects.create_user(username=username, password="pass12345", role=User.Role.STUDENT,
                                         first_name=username.title(), last_name="Demo")
            return Student.objects.create(user=u, student_number=number, curriculum=cls.curriculum, year_level=year)

        cls.studentA = mkstudent("rpt_a", "RPT-0001", 1)
        cls.studentB = mkstudent("rpt_b", "RPT-0002", 2)
        cls.studentC = mkstudent("rpt_c", "RPT-0003", 1)

        cls.enrA = Enrollment.objects.create(student=cls.studentA, term=cls.term1, status=Enrollment.Status.CONFIRMED)
        EnrollmentDetail.objects.create(enrollment=cls.enrA, section=cls.sec1, status=EnrollmentDetail.Status.ENROLLED)
        EnrollmentDetail.objects.create(enrollment=cls.enrA, section=cls.sec2, status=EnrollmentDetail.Status.ENROLLED)
        cls.enrB = Enrollment.objects.create(student=cls.studentB, term=cls.term1, status=Enrollment.Status.CONFIRMED)
        EnrollmentDetail.objects.create(enrollment=cls.enrB, section=cls.sec1, status=EnrollmentDetail.Status.ENROLLED)
        # cancelled enrollment (must be excluded everywhere)
        cls.enrC = Enrollment.objects.create(student=cls.studentC, term=cls.term1, status=Enrollment.Status.CANCELLED)
        EnrollmentDetail.objects.create(enrollment=cls.enrC, section=cls.sec1, status=EnrollmentDetail.Status.ENROLLED)

        # finance: assessment + payments with varied statuses
        cls.assessment = Assessment.objects.create(enrollment=cls.enrA, total_amount=D("5000.00"),
                                                   status=Assessment.Status.FINALIZED)
        cls.cashier = User.objects.create_user(username="rpt_cashier", password="pass12345", role=User.Role.CASHIER)
        cls.registrar = User.objects.create_user(username="rpt_registrar", password="pass12345", role=User.Role.REGISTRAR)
        cls.admin = User.objects.create_user(username="rpt_admin", password="pass12345", role=User.Role.ADMINISTRATOR)
        cls.instructor = User.objects.create_user(username="rpt_instr", password="pass12345", role=User.Role.INSTRUCTOR)

        def mkpay(receipt, amount, status, method, day):
            return Payment.objects.create(
                assessment=cls.assessment, received_by=cls.cashier, receipt_number=receipt,
                amount=D(amount), method=method, status=status,
                payment_date=datetime(2026, 9, day, 10, 0, tzinfo=dt_tz.utc))

        mkpay("RC-REC", "1000.00", Payment.Status.RECEIVED, Payment.Method.CASH, 1)
        mkpay("RC-PEND", "500.00", Payment.Status.PENDING, Payment.Method.CASH, 2)
        mkpay("RC-CAN", "500.00", Payment.Status.CANCELLED, Payment.Method.CASH, 3)
        mkpay("RC-REV", "300.00", Payment.Status.REVERSED, Payment.Method.BANK_TRANSFER, 4)
        ScholarshipAward.objects.create(student=cls.studentA, sponsor="DemoFund", amount=D("2000.00"),
                                        assessment=cls.assessment, status=ScholarshipAward.Status.APPROVED)

    def login(self, username):
        self.client.login(username=username, password="pass12345")


class CsvHelperTests(TestCase):
    def test_formula_injection_prefixed(self):
        self.assertEqual(_csv_safe("=1+1"), "'=1+1")
        self.assertEqual(_csv_safe("+x"), "'+x")
        self.assertEqual(_csv_safe("-x"), "'-x")
        self.assertEqual(_csv_safe("@x"), "'@x")
        self.assertEqual(_csv_safe("normal"), "normal")


class EnrolledReportTests(ReportTestBase):
    def test_rows_exclude_cancelled_and_no_duplicates(self):
        self.login("rpt_registrar")
        resp = self.client.get(reverse("reports:enrolled"))
        self.assertEqual(resp.status_code, 200)
        rows = resp.context["rows"]
        # A has 2 courses -> 2 rows; B has 1 -> 1 row; C cancelled -> 0. Total 3.
        self.assertEqual(len(rows), 3)
        numbers = [r["student_number"] for r in rows]
        self.assertNotIn("RPT-0003", numbers)  # cancelled excluded
        self.assertEqual(numbers.count("RPT-0001"), 2)  # two distinct courses, not duplicated further

    def test_course_filter_and_empty(self):
        self.login("rpt_admin")
        resp = self.client.get(reverse("reports:enrolled"), {"course": self.course2.id})
        self.assertEqual(len(resp.context["rows"]), 1)  # only A in course2
        resp2 = self.client.get(reverse("reports:enrolled"), {"term": self.term2.id})
        self.assertEqual(len(resp2.context["rows"]), 0)

    def test_csv_matches_display(self):
        self.login("rpt_registrar")
        resp = self.client.get(reverse("reports:enrolled"), {"format": "csv"})
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("attachment; filename=", resp["Content-Disposition"])
        body = resp.content.decode("utf-8-sig")
        self.assertIn("Student No.", body)
        self.assertIn("RPT-0001", body)
        self.assertNotIn("RPT-0003", body)  # cancelled excluded
        self.assertEqual(body.strip().count("\n"), 3)  # header + 3 rows


class SemesterReportTests(ReportTestBase):
    def test_distinct_vs_records_excludes_cancelled(self):
        self.login("rpt_admin")
        resp = self.client.get(reverse("reports:semester"))
        row = [r for r in resp.context["rows"] if r["term"] == self.term1][0]
        self.assertEqual(row["distinct_students"], 2)  # A, B (C cancelled)
        self.assertEqual(row["records"], 2)            # A multi-course still 1 record

    def test_year_filter(self):
        self.login("rpt_admin")
        resp = self.client.get(reverse("reports:semester"), {"academic_year": "2025-2026"})
        years = {r["academic_year"] for r in resp.context["rows"]}
        self.assertEqual(years, {"2025-2026"})


class CollectionReportTests(ReportTestBase):
    def test_only_received_counted_scholarship_separate(self):
        self.login("rpt_cashier")
        resp = self.client.get(reverse("reports:collection"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["payments_total"], D("1000.00"))  # only RC-REC
        self.assertEqual(resp.context["payments_count"], 1)
        self.assertEqual(resp.context["scholarship_total"], D("2000.00"))  # separate
        methods = {m["method"] for m in resp.context["by_method"]}
        self.assertEqual(methods, {"CASH"})  # reversed bank transfer excluded

    def test_method_and_date_filters(self):
        self.login("rpt_admin")
        r1 = self.client.get(reverse("reports:collection"), {"method": "BANK_TRANSFER"})
        self.assertEqual(r1.context["payments_total"], D("0.00"))  # the only BT was reversed
        r2 = self.client.get(reverse("reports:collection"), {"date_from": "2026-09-02"})
        self.assertEqual(r2.context["payments_total"], D("0.00"))  # RC-REC was day 1

    def test_csv_totals_match(self):
        self.login("rpt_admin")
        resp = self.client.get(reverse("reports:collection"), {"format": "csv"})
        body = resp.content.decode("utf-8-sig")
        self.assertIn("TOTAL RECORDED COLLECTIONS", body)
        self.assertIn("1000.00", body)
        self.assertIn("SCHOLARSHIP FUNDING (separate, not cash)", body)
        self.assertIn("2000.00", body)


class ReportPermissionTests(ReportTestBase):
    def test_enrolled_and_semester_access(self):
        for url_name in ("reports:enrolled", "reports:semester"):
            url = reverse(url_name)
            for who, code in [("rpt_registrar", 200), ("rpt_admin", 200),
                              ("rpt_cashier", 403), ("rpt_instr", 403), ("rpt_a", 403)]:
                self.login(who)
                self.assertEqual(self.client.get(url).status_code, code, f"{url_name}/{who}")
                self.client.logout()

    def test_collection_access(self):
        url = reverse("reports:collection")
        for who, code in [("rpt_cashier", 200), ("rpt_admin", 200),
                          ("rpt_registrar", 403), ("rpt_instr", 403), ("rpt_a", 403)]:
            self.login(who)
            self.assertEqual(self.client.get(url).status_code, code, who)
            self.client.logout()

    def test_export_endpoints_enforce_same_permissions(self):
        self.login("rpt_cashier")
        # cashier cannot export enrolled report
        self.assertEqual(self.client.get(reverse("reports:enrolled"), {"format": "csv"}).status_code, 403)
        # but can export collection
        self.assertEqual(self.client.get(reverse("reports:collection"), {"format": "csv"}).status_code, 200)

    def test_anonymous_redirected(self):
        self.assertEqual(self.client.get(reverse("reports:index")).status_code, 302)
