"""Milestone B finance tests: fee rules, assessment lifecycle, payments &
allocations, adjustments/scholarships, balance integrity, and permissions."""

from datetime import time
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from academics.models import (
    AcademicTerm, College, Course, Curriculum, CurriculumCourse, Program, Student,
)
from enrollment.models import Enrollment, EnrollmentDetail
from scheduling.models import Section
from finance.models import (
    Adjustment, Assessment, AssessmentVersion, FeeRule, Payment,
    PaymentAllocation, ScholarshipAward,
)
from finance import services as fs

D = Decimal


class FinanceTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.college = College.objects.create(college_code="FIN-C", name="Finance College")
        cls.program = Program.objects.create(college=cls.college, program_code="FIN-BS", name="Finance Program")
        cls.curriculum = Curriculum.objects.create(program=cls.program, curriculum_code="FIN-CUR", effective_year=2026)
        cls.term = AcademicTerm.objects.create(
            academic_year="2026-2027", semester_number=1,
            start_date="2026-08-01", end_date="2026-12-15", enrollment_open=True)
        cls.course = Course.objects.create(course_code="FIN101", title="Course 1", units=D("3.0"))
        CurriculumCourse.objects.create(
            curriculum=cls.curriculum, course=cls.course, year_level=1,
            recommended_semester=1, course_category="CORE")
        cls.student_user = User.objects.create_user(username="fin_student", password="pass12345", role=User.Role.STUDENT)
        cls.student = Student.objects.create(
            user=cls.student_user, student_number="FIN-0001",
            curriculum=cls.curriculum, year_level=1)
        cls.enrollment = Enrollment.objects.create(
            student=cls.student, term=cls.term, status=Enrollment.Status.CONFIRMED)
        cls.section = Section.objects.create(
            course=cls.course, term=cls.term, section_code="F1", capacity=40,
            day_of_week=0, start_time=time(8, 0), end_time=time(9, 30))
        EnrollmentDetail.objects.create(
            enrollment=cls.enrollment, section=cls.section,
            status=EnrollmentDetail.Status.ENROLLED)
        cls.cashier = User.objects.create_user(username="fin_cashier", password="pass12345", role=User.Role.CASHIER)
        cls.registrar = User.objects.create_user(username="fin_registrar", password="pass12345", role=User.Role.REGISTRAR)
        cls.admin = User.objects.create_user(username="fin_admin", password="pass12345", role=User.Role.ADMINISTRATOR)
        cls.admin2 = User.objects.create_user(username="fin_admin2", password="pass12345", role=User.Role.ADMINISTRATOR)

    def _tuition_general(self, amount="500"):
        return FeeRule.objects.create(
            name="Tuition", category="TUITION", scope="GENERAL",
            computation="PER_UNIT", amount=D(amount), is_demo=True)

    def _misc_general(self, amount="1000"):
        return FeeRule.objects.create(
            name="Miscellaneous", category="MISCELLANEOUS", scope="GENERAL",
            computation="FIXED", amount=D(amount), is_demo=True)


class FeeComputationTests(FinanceTestBase):
    def test_general_per_unit_and_fixed_stack_across_categories(self):
        self._tuition_general("500")   # 3 units * 500 = 1500
        self._misc_general("1000")     # fixed 1000
        result = fs.compute_fee_breakdown(self.enrollment)
        self.assertEqual(result["conflicts"], [])
        total = sum(line["line_total"] for line in result["lines"])
        self.assertEqual(total, D("2500.00"))

    def test_fixed_fee_not_multiplied_by_units(self):
        self._misc_general("1000")
        line = fs.compute_fee_breakdown(self.enrollment)["lines"][0]
        self.assertEqual(line["line_total"], D("1000.00"))
        self.assertIsNone(line["quantity"])

    def test_course_scope_overrides_general_same_category(self):
        self._tuition_general("500")  # general 500/unit
        FeeRule.objects.create(
            name="Special tuition", category="TUITION", scope="COURSE",
            course=self.course, computation="PER_UNIT", amount=D("600"), is_demo=True)
        result = fs.compute_fee_breakdown(self.enrollment)
        # course rule wins for this course: 3 * 600 = 1800 (general suppressed)
        tuition = [l for l in result["lines"] if l["fee_category"] == "TUITION"]
        self.assertEqual(len(tuition), 1)
        self.assertEqual(tuition[0]["line_total"], D("1800.00"))

    def test_conflicting_equal_rules_detected(self):
        self._misc_general("1000")
        self._misc_general("1200")  # two general MISC rules -> conflict
        result = fs.compute_fee_breakdown(self.enrollment)
        self.assertTrue(result["conflicts"])

    def test_inactive_and_wrong_term_rules_ignored(self):
        r = self._tuition_general("500")
        r.is_active = False
        r.save()
        other_term = AcademicTerm.objects.create(
            academic_year="2099-2100", semester_number=1,
            start_date="2099-08-01", end_date="2099-12-15")
        FeeRule.objects.create(name="T2", category="TUITION", scope="GENERAL",
                               computation="PER_UNIT", amount=D("999"), term=other_term)
        self.assertEqual(fs.compute_fee_breakdown(self.enrollment)["lines"], [])


class AssessmentLifecycleTests(FinanceTestBase):
    def test_draft_created_only_for_confirmed_enrollment(self):
        self._tuition_general("500")
        self._misc_general("1000")
        a = fs.create_draft_assessment(enrollment=self.enrollment, by=self.registrar)
        self.assertEqual(a.status, Assessment.Status.DRAFT)
        self.assertEqual(a.current_version.version_number, 1)
        self.assertEqual(a.total_amount, D("2500.00"))

        draft_enr = Enrollment.objects.create(
            student=self.student, term=AcademicTerm.objects.create(
                academic_year="2027-2028", semester_number=1,
                start_date="2027-08-01", end_date="2027-12-15"),
            status=Enrollment.Status.DRAFT)
        with self.assertRaises(ValidationError):
            fs.create_draft_assessment(enrollment=draft_enr, by=self.registrar)

    def test_finalize_locks_values_and_blocks_on_conflict(self):
        self._tuition_general("500")
        a = fs.create_draft_assessment(enrollment=self.enrollment, by=self.registrar)
        v = fs.finalize_assessment(assessment=a, by=self.registrar)
        self.assertEqual(v.status, AssessmentVersion.Status.FINALIZED)
        self.assertEqual(v.finalized_by_id, self.registrar.id)
        a.refresh_from_db()
        self.assertTrue(a.is_finalized)
        # second finalize -> rejected
        with self.assertRaises(ValidationError):
            fs.finalize_assessment(assessment=a, by=self.registrar)

    def test_revision_creates_new_version_and_balance_uses_current_only(self):
        self._tuition_general("500")  # total 1500
        a = fs.create_draft_assessment(enrollment=self.enrollment, by=self.registrar)
        fs.finalize_assessment(assessment=a, by=self.registrar)
        self.assertEqual(fs.assessment_balance(assessment=a), D("1500.00"))
        # change fee rules, revise
        self._misc_general("1000")  # now total would be 2500
        new_v = fs.revise_assessment(assessment=a, by=self.admin, reason="added misc")
        self.assertEqual(new_v.version_number, 2)
        fs.finalize_assessment(assessment=a, by=self.admin)
        a.refresh_from_db()
        # balance uses ONLY current version total (2500), not 1500+2500
        self.assertEqual(fs.assessment_balance(assessment=a), D("2500.00"))
        self.assertEqual(AssessmentVersion.objects.filter(assessment=a).count(), 2)
        old = AssessmentVersion.objects.get(assessment=a, version_number=1)
        self.assertEqual(old.status, AssessmentVersion.Status.SUPERSEDED)
        self.assertEqual(old.total_amount, D("1500.00"))  # unchanged


class PaymentAllocationTests(FinanceTestBase):
    def _finalized(self):
        self._tuition_general("500")  # total 1500
        a = fs.create_draft_assessment(enrollment=self.enrollment, by=self.registrar)
        fs.finalize_assessment(assessment=a, by=self.registrar)
        return a

    def test_received_payment_reduces_balance_once(self):
        a = self._finalized()
        fs.record_payment(assessment=a, received_by=self.cashier,
                          receipt_number="R1", amount=D("1000"), method="CASH")
        self.assertEqual(fs.assessment_balance(assessment=a), D("500.00"))
        self.assertEqual(PaymentAllocation.objects.count(), 1)

    def test_pending_and_cancelled_do_not_reduce_balance(self):
        a = self._finalized()
        fs.record_payment(assessment=a, received_by=self.cashier,
                          receipt_number="P1", amount=D("1000"), method="CASH",
                          status=Payment.Status.PENDING)
        fs.record_payment(assessment=a, received_by=self.cashier,
                          receipt_number="C1", amount=D("1000"), method="CASH",
                          status=Payment.Status.CANCELLED)
        self.assertEqual(fs.assessment_balance(assessment=a), D("1500.00"))

    def test_reversed_payment_no_longer_counts(self):
        a = self._finalized()
        p = fs.record_payment(assessment=a, received_by=self.cashier,
                              receipt_number="R2", amount=D("1000"), method="CASH")
        self.assertEqual(fs.assessment_balance(assessment=a), D("500.00"))
        fs.reverse_payment(payment=p, by=self.admin, reason="error")
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.Status.REVERSED)
        self.assertEqual(fs.assessment_balance(assessment=a), D("1500.00"))
        self.assertTrue(Adjustment.objects.filter(payment=p, adjustment_type="REVERSAL").exists())

    def test_overpayment_caps_allocation_and_balance_not_negative(self):
        a = self._finalized()
        p = fs.record_payment(assessment=a, received_by=self.cashier,
                              receipt_number="OP", amount=D("2000"), method="CASH")
        self.assertEqual(fs.assessment_balance(assessment=a), D("0.00"))
        self.assertEqual(p.allocated_amount, D("1500.00"))
        self.assertEqual(p.unallocated_amount, D("500.00"))

    def test_duplicate_receipt_rejected(self):
        a = self._finalized()
        fs.record_payment(assessment=a, received_by=self.cashier,
                          receipt_number="DUP", amount=D("100"), method="CASH")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                fs.record_payment(assessment=a, received_by=self.cashier,
                                  receipt_number="DUP", amount=D("100"), method="CASH")

    def test_allocation_cannot_exceed_unallocated(self):
        a = self._finalized()
        p = fs.record_payment(assessment=a, received_by=self.cashier,
                              receipt_number="AL", amount=D("1000"), method="CASH")
        # already auto-allocated 1000; no remainder
        with self.assertRaises(ValidationError):
            fs.allocate_payment(payment=p, version=a.current_version, amount=D("1"), by=self.cashier)


class AdjustmentScholarshipTests(FinanceTestBase):
    def _finalized(self):
        self._tuition_general("500")
        a = fs.create_draft_assessment(enrollment=self.enrollment, by=self.registrar)
        fs.finalize_assessment(assessment=a, by=self.registrar)
        return a

    def test_credit_requires_approval_and_creator_cannot_approve(self):
        a = self._finalized()
        adj = fs.create_adjustment(adjustment_type="CREDIT", amount=D("200"),
                                   reason="goodwill", by=self.cashier, assessment=a)
        # unapproved credit does not change balance
        self.assertEqual(fs.assessment_balance(assessment=a), D("1500.00"))
        with self.assertRaises(ValidationError):
            fs.approve_adjustment(adjustment=adj, by=self.cashier)  # creator
        fs.approve_adjustment(adjustment=adj, by=self.admin)
        self.assertEqual(fs.assessment_balance(assessment=a), D("1300.00"))

    def test_refund_increases_balance_after_approval(self):
        a = self._finalized()
        fs.record_payment(assessment=a, received_by=self.cashier,
                          receipt_number="PF", amount=D("1500"), method="CASH")
        self.assertEqual(fs.assessment_balance(assessment=a), D("0.00"))
        adj = fs.create_adjustment(adjustment_type="REFUND", amount=D("500"),
                                   reason="overpaid elsewhere", by=self.cashier, assessment=a)
        fs.approve_adjustment(adjustment=adj, by=self.admin)
        self.assertEqual(fs.assessment_balance(assessment=a), D("500.00"))

    def test_scholarship_counts_when_approved_and_not_as_cash(self):
        a = self._finalized()
        sch = fs.create_scholarship(student=self.student, sponsor="DemoFund",
                                    amount=D("500"), by=self.cashier, assessment=a)
        self.assertEqual(fs.assessment_balance(assessment=a), D("1500.00"))  # pending
        with self.assertRaises(ValidationError):
            fs.approve_scholarship(scholarship=sch, by=self.cashier)  # creator
        fs.approve_scholarship(scholarship=sch, by=self.admin)
        self.assertEqual(fs.assessment_balance(assessment=a), D("1000.00"))
        # scholarship is not a payment
        self.assertEqual(Payment.objects.filter(assessment=a).count(), 0)


class FinancePermissionTests(FinanceTestBase):
    def _finalized(self):
        self._tuition_general("500")
        a = fs.create_draft_assessment(enrollment=self.enrollment, by=self.registrar)
        fs.finalize_assessment(assessment=a, by=self.registrar)
        return a

    def test_finance_list_access_by_role(self):
        url = reverse("finance:assessment_list")
        for who, code in [("fin_cashier", 200), ("fin_registrar", 200),
                          ("fin_admin", 200), ("fin_student", 403)]:
            self.client.login(username=who, password="pass12345")
            self.assertEqual(self.client.get(url).status_code, code, who)
            self.client.logout()

    def test_cashier_cannot_finalize_registrar_can(self):
        a = fs.create_draft_assessment(enrollment=self.enrollment, by=self.registrar)
        self._tuition_general("500")
        url = reverse("finance:finalize", args=[a.pk])
        self.client.login(username="fin_cashier", password="pass12345")
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.logout()
        self.client.login(username="fin_registrar", password="pass12345")
        self.assertEqual(self.client.post(url).status_code, 302)  # redirect after finalize
        a.refresh_from_db()
        self.assertTrue(a.is_finalized)

    def test_record_payment_cashier_only(self):
        a = self._finalized()
        url = reverse("finance:record_payment", args=[a.pk])
        self.client.login(username="fin_registrar", password="pass12345")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.logout()
        self.client.login(username="fin_cashier", password="pass12345")
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_approvals_admin_only(self):
        url = reverse("finance:approvals")
        self.client.login(username="fin_cashier", password="pass12345")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.logout()
        self.client.login(username="fin_admin", password="pass12345")
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_student_and_instructor_blocked_from_detail(self):
        a = self._finalized()
        url = reverse("finance:assessment_detail", args=[a.pk])
        self.client.login(username="fin_student", password="pass12345")
        self.assertEqual(self.client.get(url).status_code, 403)
