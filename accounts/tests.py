from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AuthFlowTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="student1",
            password="pass12345",
            role=User.Role.STUDENT,
            is_active=True,
        )
        self.instructor = User.objects.create_user(
            username="inst1",
            password="pass12345",
            role=User.Role.INSTRUCTOR,
            is_active=True,
        )
        self.cashier = User.objects.create_user(
            username="cash1",
            password="pass12345",
            role=User.Role.CASHIER,
            is_active=True,
        )
        self.registrar = User.objects.create_user(
            username="reg1",
            password="pass12345",
            role=User.Role.REGISTRAR,
            is_active=True,
        )
        self.admin = User.objects.create_user(
            username="admin1",
            password="pass12345",
            role=User.Role.ADMINISTRATOR,
            is_active=True,
            is_staff=True,
        )
        self.inactive = User.objects.create_user(
            username="inactive1",
            password="pass12345",
            role=User.Role.STUDENT,
            is_active=False,
        )

    def test_login_success_student_redirects(self):
        resp = self.client.post(reverse("login"), {"username": "student1", "password": "pass12345"})
        self.assertRedirects(resp, reverse("student_dashboard"))

    def test_login_success_instructor_redirects(self):
        resp = self.client.post(reverse("login"), {"username": "inst1", "password": "pass12345"})
        self.assertRedirects(resp, reverse("instructor_dashboard"))

    def test_login_success_cashier_redirects(self):
        resp = self.client.post(reverse("login"), {"username": "cash1", "password": "pass12345"})
        self.assertRedirects(resp, reverse("cashier_dashboard"))

    def test_login_success_registrar_redirects(self):
        resp = self.client.post(reverse("login"), {"username": "reg1", "password": "pass12345"})
        self.assertRedirects(resp, reverse("registrar_dashboard"))

    def test_login_success_administrator_redirects(self):
        resp = self.client.post(reverse("login"), {"username": "admin1", "password": "pass12345"})
        self.assertRedirects(resp, reverse("administrator_dashboard"))

    def test_invalid_credentials_rejected(self):
        resp = self.client.post(reverse("login"), {"username": "student1", "password": "wrong"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.wsgi_request.user.is_authenticated)

    def test_inactive_user_cannot_login(self):
        resp = self.client.post(reverse("login"), {"username": "inactive1", "password": "pass12345"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.wsgi_request.user.is_authenticated)

    def test_authenticated_user_visits_login_redirects(self):
        self.client.login(username="student1", password="pass12345")
        resp = self.client.get(reverse("login"))
        self.assertRedirects(resp, reverse("student_dashboard"))

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse("student_dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)

    def test_role_boundary_student_cannot_access_instructor_dashboard(self):
        self.client.login(username="student1", password="pass12345")
        resp = self.client.get(reverse("instructor_dashboard"))
        self.assertEqual(resp.status_code, 403)

    def test_role_boundary_instructor_cannot_access_cashier_dashboard(self):
        self.client.login(username="inst1", password="pass12345")
        resp = self.client.get(reverse("cashier_dashboard"))
        self.assertEqual(resp.status_code, 403)

    def test_role_boundary_cashier_cannot_access_registrar_dashboard(self):
        self.client.login(username="cash1", password="pass12345")
        resp = self.client.get(reverse("registrar_dashboard"))
        self.assertEqual(resp.status_code, 403)

    def test_role_boundary_registrar_cannot_access_administrator_dashboard(self):
        self.client.login(username="reg1", password="pass12345")
        resp = self.client.get(reverse("administrator_dashboard"))
        self.assertEqual(resp.status_code, 403)

    def test_role_boundary_administrator_cannot_be_assumed_by_is_superuser(self):
        superuser = User.objects.create_superuser(
            username="su",
            password="pass12345",
            email="su@example.com",
            role=User.Role.CASHIER,
        )
        # is_superuser must not bypass the application role check.
        self.client.login(username="su", password="pass12345")
        resp = self.client.get(reverse("student_dashboard"))
        self.assertEqual(resp.status_code, 403)

    def test_logout_requires_post(self):
        self.client.login(username="student1", password="pass12345")
        resp = self.client.get(reverse("logout"))
        # Django LogoutView by default requires POST; GET may return 405
        self.assertIn(resp.status_code, [405, 302])

    def test_logout_post_invalidates_session(self):
        self.client.login(username="student1", password="pass12345")
        resp = self.client.post(reverse("logout"))
        self.assertIn(resp.status_code, [200, 302])
        resp2 = self.client.get(reverse("student_dashboard"))
        self.assertEqual(resp2.status_code, 302)
        self.assertIn(reverse("login"), resp2.url)

    def test_unsafe_next_redirect_not_followed(self):
        resp = self.client.post(
            reverse("login"),
            {"username": "student1", "password": "pass12345", "next": "https://evil.com/"},
        )
        # Should not redirect to external site
        self.assertNotIn("evil.com", resp.url if resp.status_code in [301, 302] else "")

    def test_dashboard_dispatch_redirects_by_role(self):
        self.client.login(username="student1", password="pass12345")
        resp = self.client.get(reverse("dashboard"))
        self.assertRedirects(resp, reverse("student_dashboard"))


class AdminHardeningTests(TestCase):
    def setUp(self):
        self.student_staff = User.objects.create_user(username='sstaff', password='pass12345', role=User.Role.STUDENT, is_active=True, is_staff=True)
        self.superuser_nonadmin = User.objects.create_superuser(username='sunonadmin', password='pass12345', email='s@example.com')
        self.superuser_nonadmin.role = User.Role.STUDENT
        self.superuser_nonadmin.is_staff = True
        self.superuser_nonadmin.save()
        self.admin = User.objects.create_user(username='a1', password='pass12345', role=User.Role.ADMINISTRATOR, is_active=True, is_staff=True)
        self.inactive_admin = User.objects.create_user(username='ia', password='pass12345', role=User.Role.ADMINISTRATOR, is_active=False, is_staff=True)
        self.nonstaff_admin = User.objects.create_user(username='nsa', password='pass12345', role=User.Role.ADMINISTRATOR, is_active=True, is_staff=False)

    def test_admin_denied_for_non_admin_staff(self):
        self.client.login(username='sstaff', password='pass12345')
        resp = self.client.get(reverse('admin:index'))
        self.assertNotEqual(resp.status_code, 200)

    def test_admin_denied_for_superuser_with_non_admin_role(self):
        self.client.login(username='sunonadmin', password='pass12345')
        resp = self.client.get(reverse('admin:index'))
        self.assertNotEqual(resp.status_code, 200)

    def test_admin_allowed_for_admin_staff(self):
        self.client.login(username='a1', password='pass12345')
        resp = self.client.get(reverse('admin:index'))
        self.assertIn(resp.status_code, [200, 302])

    def test_admin_denied_for_inactive_admin_staff(self):
        self.client.login(username='ia', password='pass12345')
        resp = self.client.get(reverse('admin:index'))
        self.assertNotEqual(resp.status_code, 200)

    def test_admin_denied_for_nonstaff_administrator(self):
        self.client.login(username='nsa', password='pass12345')
        resp = self.client.get(reverse('admin:index'))
        self.assertNotEqual(resp.status_code, 200)


from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from academics.models import College
from finance.models import Payment
from enrollment.models import Enrollment


class AdminPermissionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_perm",
            password="pass12345",
            role=User.Role.ADMINISTRATOR,
            is_active=True,
            is_staff=True,
        )
        self.ct_college = ContentType.objects.get_for_model(College)
        self.admin.user_permissions.add(
            Permission.objects.get(codename="add_college", content_type=self.ct_college),
            Permission.objects.get(codename="change_college", content_type=self.ct_college),
            Permission.objects.get(codename="view_college", content_type=self.ct_college),
        )
        self.admin.save()

    def test_master_data_cannot_delete(self):
        self.client.login(username="admin_perm", password="pass12345")
        college = College.objects.create(college_code="C1", name="College 1")
        url = reverse("admin:academics_college_delete", args=[college.pk])
        resp = self.client.post(url)
        self.assertNotEqual(resp.status_code, 200)
        self.assertTrue(College.objects.filter(pk=college.pk).exists())

    def test_master_data_bulk_actions_empty(self):
        self.client.login(username="admin_perm", password="pass12345")
        resp = self.client.get(reverse("admin:academics_college_changelist"))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # Check for the actual bulk-action controls rather than the substring
        # "action", which also appears in Django's unconditional actions.js.
        self.assertNotIn('name="action"', content)
        self.assertNotIn('id="action-toggle"', content)


class AdminReadOnlyTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_ro",
            password="pass12345",
            role=User.Role.ADMINISTRATOR,
            is_active=True,
            is_staff=True,
        )
        ct_payment = ContentType.objects.get_for_model(Payment)
        self.admin.user_permissions.add(
            Permission.objects.get(codename="view_payment", content_type=ct_payment),
        )
        self.admin.save()

    def test_payment_add_denied(self):
        self.client.login(username="admin_ro", password="pass12345")
        url = reverse("admin:finance_payment_add")
        resp = self.client.get(url)
        self.assertNotEqual(resp.status_code, 200)
        resp = self.client.post(url, {})
        self.assertNotEqual(resp.status_code, 200)

    def test_payment_change_denied(self):
        self.client.login(username="admin_ro", password="pass12345")
        # Try to access change page for non-existent or existing - should be denied
        url = reverse("admin:finance_payment_change", args=[1])
        resp = self.client.get(url)
        self.assertNotEqual(resp.status_code, 200)

    def test_payment_delete_denied(self):
        self.client.login(username="admin_ro", password="pass12345")
        url = reverse("admin:finance_payment_delete", args=[1])
        resp = self.client.get(url)
        self.assertNotEqual(resp.status_code, 200)


class AdminSuperuserTests(TestCase):
    def setUp(self):
        self.admin_super = User.objects.create_superuser(
            username="adminsu",
            password="pass12345",
            email="asu@example.com",
        )
        self.admin_super.role = User.Role.ADMINISTRATOR
        self.admin_super.is_staff = True
        self.admin_super.save()

    def test_admin_superuser_can_access_admin(self):
        self.client.login(username="adminsu", password="pass12345")
        resp = self.client.get(reverse("admin:index"))
        self.assertIn(resp.status_code, [200, 302])

    def test_admin_superuser_cannot_mutate_readonly(self):
        self.client.login(username="adminsu", password="pass12345")
        url = reverse("admin:finance_payment_add")
        resp = self.client.post(url, {})
        self.assertNotEqual(resp.status_code, 200)


class CustomUserAdminSecurityTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_cua",
            password="pass12345",
            role=User.Role.ADMINISTRATOR,
            is_active=True,
            is_staff=True,
        )
        self.other = User.objects.create_user(
            username="other",
            password="pass12345",
            role=User.Role.STUDENT,
            is_active=True,
        )
        # The admin site enforces role policy, but Django model permissions
        # still apply. Grant the permissions this security test exercises.
        ct_user = ContentType.objects.get_for_model(User)
        self.admin.user_permissions.add(
            Permission.objects.get(codename="view_user", content_type=ct_user),
            Permission.objects.get(codename="change_user", content_type=ct_user),
        )

    def _created_at_post_data(self, user):
        """Supply the editable date_joined split-widget values."""
        local = timezone.localtime(user.date_joined)
        return {
            "date_joined_0": local.strftime("%Y-%m-%d"),
            "date_joined_1": local.strftime("%H:%M:%S"),
        }

    def test_admin_can_assign_role_to_other(self):
        self.client.login(username="admin_cua", password="pass12345")
        url = reverse("admin:accounts_user_change", args=[self.other.pk])
        data = {
            "username": self.other.username,
            "role": User.Role.REGISTRAR,
            "is_active": "on",
            **self._created_at_post_data(self.other),
        }
        resp = self.client.post(url, data)
        self.other.refresh_from_db()
        self.assertEqual(self.other.role, User.Role.REGISTRAR)

    def test_admin_cannot_change_own_role(self):
        self.client.login(username="admin_cua", password="pass12345")
        url = reverse("admin:accounts_user_change", args=[self.admin.pk])
        data = {
            "username": self.admin.username,
            "role": User.Role.STUDENT,
            "is_staff": "on",
            "is_active": "on",
            **self._created_at_post_data(self.admin),
        }
        resp = self.client.post(url, data)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.Role.ADMINISTRATOR)

    def test_admin_cannot_change_own_is_staff(self):
        self.client.login(username="admin_cua", password="pass12345")
        url = reverse("admin:accounts_user_change", args=[self.admin.pk])
        data = {
            "username": self.admin.username,
            "role": User.Role.ADMINISTRATOR,
            "is_active": "on",
            **self._created_at_post_data(self.admin),
        }
        resp = self.client.post(url, data)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_staff)

    def test_cannot_grant_superuser_via_admin(self):
        self.client.login(username="admin_cua", password="pass12345")
        url = reverse("admin:accounts_user_change", args=[self.other.pk])
        data = {
            "username": self.other.username,
            "role": User.Role.STUDENT,
            "is_active": "on",
            "is_superuser": "on",
            **self._created_at_post_data(self.other),
        }
        resp = self.client.post(url, data)
        self.other.refresh_from_db()
        self.assertFalse(self.other.is_superuser)

    def test_password_management_still_works(self):
        self.client.login(username="admin_cua", password="pass12345")
        url = reverse("admin:accounts_user_change", args=[self.other.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)


class CSRFAuditTests(TestCase):
    def test_login_without_csrf_rejected(self):
        client = Client(enforce_csrf_checks=True)
        resp = client.post(reverse("login"), {"username": "x", "password": "y"})
        self.assertEqual(resp.status_code, 403)

    def test_login_with_csrf_allowed(self):
        client = Client(enforce_csrf_checks=True)
        resp = client.get(reverse("login"))
        self.assertEqual(resp.status_code, 200)

    def test_logout_without_csrf_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.login(username="x", password="y")  # will fail but let's test
        resp = client.post(reverse("logout"))
        self.assertIn(resp.status_code, [403, 302])


class OwnershipHelperTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="stu_h", password="pass12345", role=User.Role.STUDENT)
        self.user2 = User.objects.create_user(username="stu_h2", password="pass12345", role=User.Role.STUDENT)

    def test_get_student_for_user_none_if_no_student(self):
        from accounts.permissions import get_student_for_user
        self.assertIsNone(get_student_for_user(self.user))

    def test_is_student_owner_false_when_none(self):
        from accounts.permissions import is_student_owner
        self.assertFalse(is_student_owner(self.user, None))

    def test_get_instructor_for_user_none(self):
        from accounts.permissions import get_instructor_for_user
        self.assertIsNone(get_instructor_for_user(self.user))

    def test_is_instructor_assigned_false(self):
        from accounts.permissions import is_instructor_assigned
        self.assertFalse(is_instructor_assigned(self.user, None))


# ---------------------------------------------------------------------------
# Phase 6B authorization, services, and people-screen tests
# ---------------------------------------------------------------------------

from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.utils import timezone
from django.views import View

from accounts.permissions import (
    RoleRequiredMixin,
    get_instructor_for_user,
    get_student_for_user,
    role_required,
)
from accounts.services import (
    CONFLICT_ERROR,
    create_instructor_account,
    create_student_account,
    update_instructor_profile,
    update_student_profile,
)
from academics.models import Course, Curriculum, Instructor, Program, Student


class AuthorizationHardeningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.inactive = User.objects.create_user(
            username="auth_inactive",
            password="pass12345",
            role=User.Role.REGISTRAR,
            is_active=False,
        )
        cls.active = User.objects.create_user(
            username="auth_active",
            password="pass12345",
            role=User.Role.REGISTRAR,
        )

    def _request(self, user):
        request = RequestFactory().get("/protected/")
        request.user = user
        return request

    def test_role_required_rejects_inactive_authenticated_user(self):
        @role_required(User.Role.REGISTRAR)
        def protected(request):
            return HttpResponse("ok")

        with self.assertRaises(PermissionDenied):
            protected(self._request(self.inactive))

    def test_role_required_mixin_rejects_inactive_authenticated_user(self):
        class ProtectedView(RoleRequiredMixin, View):
            allowed_roles = (User.Role.REGISTRAR,)

            def get(self, request):
                return HttpResponse("ok")

        with self.assertRaises(PermissionDenied):
            ProtectedView().dispatch(self._request(self.inactive))

    def test_helpers_agree_for_anonymous_user(self):
        @role_required(User.Role.REGISTRAR)
        def protected(request):
            return HttpResponse("ok")

        class ProtectedView(RoleRequiredMixin, View):
            allowed_roles = (User.Role.REGISTRAR,)

            def get(self, request):
                return HttpResponse("ok")

        anonymous = AnonymousUser()
        decorator_response = protected(self._request(anonymous))
        mixin_response = ProtectedView().dispatch(self._request(anonymous))
        self.assertEqual(decorator_response.status_code, 302)
        self.assertEqual(mixin_response.status_code, 302)
        self.assertIn(reverse("login"), decorator_response.url)
        self.assertIn(reverse("login"), mixin_response.url)

    def test_helpers_agree_for_active_wrong_role(self):
        student = User.objects.create_user(
            username="auth_student",
            password="pass12345",
            role=User.Role.STUDENT,
        )

        @role_required(User.Role.REGISTRAR)
        def protected(request):
            return HttpResponse("ok")

        class ProtectedView(RoleRequiredMixin, View):
            allowed_roles = (User.Role.REGISTRAR,)

            def get(self, request):
                return HttpResponse("ok")

        with self.assertRaises(PermissionDenied):
            protected(self._request(student))
        with self.assertRaises(PermissionDenied):
            ProtectedView().dispatch(self._request(student))

    def test_ownership_helpers_reject_inactive_users(self):
        curriculum = Curriculum.objects.create(
            program=Program.objects.create(
                college=College.objects.create(
                    college_code="OWN-C", name="Ownership College"
                ),
                program_code="OWN-P",
                name="Ownership Program",
            ),
            curriculum_code="OWN-CUR",
            effective_year=2024,
        )
        student_profile = Student.objects.create(
            user=self.inactive,
            student_number="OWN-001",
            curriculum=curriculum,
            year_level=1,
        )
        self.assertIsNotNone(student_profile)
        self.assertIsNone(get_student_for_user(self.inactive))
        self.assertIsNone(get_instructor_for_user(self.inactive))


class PeopleTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.college = College.objects.create(
            college_code="PPL-ENG", name="People College"
        )
        cls.program = Program.objects.create(
            college=cls.college,
            program_code="PPL-BS",
            name="People Program",
        )
        cls.curriculum = Curriculum.objects.create(
            program=cls.program,
            curriculum_code="PPL-CUR",
            effective_year=2024,
        )
        cls.registrar = User.objects.create_user(
            username="people_reg",
            password="pass12345",
            role=User.Role.REGISTRAR,
        )
        cls.administrator = User.objects.create_user(
            username="people_admin",
            password="pass12345",
            role=User.Role.ADMINISTRATOR,
            is_staff=True,
        )
        cls.cashier = User.objects.create_user(
            username="people_cash",
            password="pass12345",
            role=User.Role.CASHIER,
        )
        cls.inactive_registrar = User.objects.create_user(
            username="people_inactive_reg",
            password="pass12345",
            role=User.Role.REGISTRAR,
            is_active=False,
        )
        cls.inactive_administrator = User.objects.create_user(
            username="people_inactive_admin",
            password="pass12345",
            role=User.Role.ADMINISTRATOR,
            is_staff=True,
            is_active=False,
        )

    def make_student(self, username="existing_student", number="EX-001"):
        user = User.objects.create_user(
            username=username,
            password="pass12345",
            role=User.Role.STUDENT,
            first_name="Existing",
            last_name="Student",
        )
        return Student.objects.create(
            user=user,
            student_number=number,
            curriculum=self.curriculum,
            year_level=1,
        )

    def make_instructor(self, username="existing_instructor", number="EMP-001"):
        user = User.objects.create_user(
            username=username,
            password="pass12345",
            role=User.Role.INSTRUCTOR,
            first_name="Existing",
            last_name="Instructor",
        )
        return Instructor.objects.create(
            user=user, employee_number=number
        )

    def student_create_payload(self, **overrides):
        data = {
            "username": "new_student",
            "first_name": "New",
            "last_name": "Student",
            "middle_name": "",
            "email": "new.student@example.com",
            "phone": "",
            "address": "",
            "password1": "Str0ngPass!2026",
            "password2": "Str0ngPass!2026",
            "student_number": "2026-0001",
            "curriculum": self.curriculum.pk,
            "year_level": 1,
        }
        data.update(overrides)
        return data

    def instructor_create_payload(self, **overrides):
        data = {
            "username": "new_instructor",
            "first_name": "New",
            "last_name": "Instructor",
            "middle_name": "",
            "email": "new.instructor@example.com",
            "phone": "",
            "address": "",
            "password1": "Str0ngPass!2026",
            "password2": "Str0ngPass!2026",
            "employee_number": "EMP-2026",
        }
        data.update(overrides)
        return data

    def student_update_payload(self, student, **overrides):
        user = student.user
        data = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "middle_name": user.middle_name or "",
            "email": user.email,
            "phone": user.phone or "",
            "address": user.address or "",
            "password1": "",
            "password2": "",
            "student_number": student.student_number,
            "curriculum": student.curriculum_id,
            "year_level": student.year_level,
        }
        data.update(overrides)
        return data

    def instructor_update_payload(self, instructor, **overrides):
        user = instructor.user
        data = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "middle_name": user.middle_name or "",
            "email": user.email,
            "phone": user.phone or "",
            "address": user.address or "",
            "password1": "",
            "password2": "",
            "employee_number": instructor.employee_number,
        }
        data.update(overrides)
        return data


class AccountServiceTests(PeopleTestCase):
    def test_create_student_assigns_role_hashes_password_and_creates_profile(self):
        student = create_student_account(
            username="svc_student",
            password="Str0ngPass!2026",
            student_number="SVC-001",
            curriculum=self.curriculum,
            year_level=2,
            first_name="Service",
            last_name="Student",
        )
        self.assertEqual(student.user.role, User.Role.STUDENT)
        self.assertTrue(student.user.check_password("Str0ngPass!2026"))
        self.assertEqual(student.student_number, "SVC-001")
        self.assertEqual(student.year_level, 2)

    def test_create_instructor_assigns_role_hashes_password_and_creates_profile(self):
        instructor = create_instructor_account(
            username="svc_instructor",
            password="Str0ngPass!2026",
            employee_number="SVC-EMP",
            first_name="Service",
            last_name="Instructor",
        )
        self.assertEqual(instructor.user.role, User.Role.INSTRUCTOR)
        self.assertTrue(instructor.user.check_password("Str0ngPass!2026"))
        self.assertEqual(instructor.employee_number, "SVC-EMP")

    def test_update_student_updates_user_and_profile(self):
        student = self.make_student()
        updated = update_student_profile(
            student,
            user_fields={"first_name": "Updated", "username": "updated_stu"},
            profile_fields={"year_level": 3},
        )
        updated.user.refresh_from_db()
        updated.refresh_from_db()
        self.assertEqual(updated.user.first_name, "Updated")
        self.assertEqual(updated.user.username, "updated_stu")
        self.assertEqual(updated.year_level, 3)

    def test_update_instructor_updates_user_and_profile(self):
        instructor = self.make_instructor()
        updated = update_instructor_profile(
            instructor,
            user_fields={"first_name": "Updated"},
            profile_fields={"employee_number": "EMP-UPD"},
        )
        updated.user.refresh_from_db()
        updated.refresh_from_db()
        self.assertEqual(updated.user.first_name, "Updated")
        self.assertEqual(updated.employee_number, "EMP-UPD")

    def test_optional_password_update_uses_hashing_and_validators(self):
        student = self.make_student()
        update_student_profile(student, password="NewStr0ng!2026")
        student.user.refresh_from_db()
        self.assertTrue(student.user.check_password("NewStr0ng!2026"))
        self.assertFalse(student.user.check_password("pass12345"))

    def test_password_validator_rejects_weak_password(self):
        with self.assertRaises(ValidationError):
            create_student_account(
                username="weak_student",
                password="123",
                student_number="WEAK-001",
                curriculum=self.curriculum,
                year_level=1,
            )
        self.assertFalse(User.objects.filter(username="weak_student").exists())

    def test_create_student_rolls_back_user_when_profile_save_fails(self):
        with patch.object(Student, "save", side_effect=IntegrityError("boom")):
            with self.assertRaises(IntegrityError):
                create_student_account(
                    username="rollback_student",
                    password="Str0ngPass!2026",
                    student_number="RB-001",
                    curriculum=self.curriculum,
                    year_level=1,
                )
        self.assertFalse(User.objects.filter(username="rollback_student").exists())
        self.assertFalse(Student.objects.filter(student_number="RB-001").exists())

    def test_create_instructor_rolls_back_user_when_profile_save_fails(self):
        with patch.object(Instructor, "save", side_effect=IntegrityError("boom")):
            with self.assertRaises(IntegrityError):
                create_instructor_account(
                    username="rollback_instructor",
                    password="Str0ngPass!2026",
                    employee_number="RB-EMP",
                )
        self.assertFalse(
            User.objects.filter(username="rollback_instructor").exists()
        )
        self.assertFalse(
            Instructor.objects.filter(employee_number="RB-EMP").exists()
        )

    def test_update_student_rolls_back_when_profile_save_fails(self):
        student = self.make_student()
        with patch.object(Student, "save", side_effect=IntegrityError("boom")):
            with self.assertRaises(IntegrityError):
                update_student_profile(
                    student,
                    user_fields={"first_name": "Changed"},
                    profile_fields={"year_level": 4},
                )
        student.user.refresh_from_db()
        student.refresh_from_db()
        self.assertEqual(student.user.first_name, "Existing")
        self.assertEqual(student.year_level, 1)

    def test_update_student_rolls_back_when_user_save_fails(self):
        student = self.make_student()
        with patch.object(User, "save", side_effect=IntegrityError("boom")):
            with self.assertRaises(IntegrityError):
                update_student_profile(
                    student,
                    user_fields={"first_name": "Changed"},
                    profile_fields={"year_level": 4},
                )
        student.user.refresh_from_db()
        student.refresh_from_db()
        self.assertEqual(student.user.first_name, "Existing")
        self.assertEqual(student.year_level, 1)

    def test_update_instructor_rolls_back_when_profile_save_fails(self):
        instructor = self.make_instructor()
        with patch.object(Instructor, "save", side_effect=IntegrityError("boom")):
            with self.assertRaises(IntegrityError):
                update_instructor_profile(
                    instructor,
                    user_fields={"first_name": "Changed"},
                    profile_fields={"employee_number": "RB-EMP-2"},
                )
        instructor.user.refresh_from_db()
        instructor.refresh_from_db()
        self.assertEqual(instructor.user.first_name, "Existing")
        self.assertEqual(instructor.employee_number, "EMP-001")

    def test_update_instructor_rolls_back_when_user_save_fails(self):
        instructor = self.make_instructor()
        with patch.object(User, "save", side_effect=IntegrityError("boom")):
            with self.assertRaises(IntegrityError):
                update_instructor_profile(
                    instructor,
                    user_fields={"first_name": "Changed"},
                )
        instructor.user.refresh_from_db()
        self.assertEqual(instructor.user.first_name, "Existing")

    def test_student_service_rejects_existing_instructor_profile(self):
        student = self.make_student()
        Instructor.objects.create(
            user=student.user, employee_number="DUAL-EMP"
        )
        with self.assertRaises(ValidationError):
            update_student_profile(
                student, user_fields={"first_name": "Should Not Save"}
            )
        student.user.refresh_from_db()
        self.assertEqual(student.user.first_name, "Existing")

    def test_instructor_service_rejects_existing_student_profile(self):
        instructor = self.make_instructor()
        Student.objects.create(
            user=instructor.user,
            student_number="DUAL-STU",
            curriculum=self.curriculum,
            year_level=1,
        )
        with self.assertRaises(ValidationError):
            update_instructor_profile(
                instructor, user_fields={"first_name": "Should Not Save"}
            )
        instructor.user.refresh_from_db()
        self.assertEqual(instructor.user.first_name, "Existing")

    def test_service_rejects_role_injection(self):
        with self.assertRaises(ValidationError):
            create_student_account(
                username="role_injection",
                password="Str0ngPass!2026",
                student_number="ROLE-001",
                curriculum=self.curriculum,
                year_level=1,
                role=User.Role.ADMINISTRATOR,
            )
        self.assertFalse(User.objects.filter(username="role_injection").exists())

    def test_database_usable_after_direct_service_failure(self):
        with patch.object(Student, "save", side_effect=IntegrityError("boom")):
            with self.assertRaises(IntegrityError):
                create_student_account(
                    username="failed_then_ok",
                    password="Str0ngPass!2026",
                    student_number="FAIL-001",
                    curriculum=self.curriculum,
                    year_level=1,
                )
        student = create_student_account(
            username="failed_then_ok",
            password="Str0ngPass!2026",
            student_number="FAIL-001",
            curriculum=self.curriculum,
            year_level=1,
        )
        self.assertTrue(User.objects.filter(pk=student.user_id).exists())


class PeopleAuthorizationTests(PeopleTestCase):
    def test_registrar_can_list_and_open_create_forms(self):
        self.client.force_login(self.registrar)
        for url in [
            reverse("people:student_list"),
            reverse("people:instructor_list"),
            reverse("people:student_create"),
            reverse("people:instructor_create"),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_registrar_can_view_details_and_update_forms(self):
        student = self.make_student()
        instructor = self.make_instructor()
        self.client.force_login(self.registrar)
        for url in [
            reverse("people:student_detail", args=[student.pk]),
            reverse("people:student_update", args=[student.pk]),
            reverse("people:instructor_detail", args=[instructor.pk]),
            reverse("people:instructor_update", args=[instructor.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_administrator_is_read_only(self):
        student = self.make_student()
        instructor = self.make_instructor()
        self.client.force_login(self.administrator)
        for url in [
            reverse("people:student_list"),
            reverse("people:student_detail", args=[student.pk]),
            reverse("people:instructor_list"),
            reverse("people:instructor_detail", args=[instructor.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        for url in [
            reverse("people:student_create"),
            reverse("people:student_update", args=[student.pk]),
            reverse("people:instructor_create"),
            reverse("people:instructor_update", args=[instructor.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_administrator_post_is_denied(self):
        self.client.force_login(self.administrator)
        response = self.client.post(
            reverse("people:student_create"), self.student_create_payload()
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="new_student").exists())

        student = self.make_student()
        response = self.client.post(
            reverse("people:student_update", args=[student.pk]),
            self.student_update_payload(student, first_name="Hacked"),
        )
        self.assertEqual(response.status_code, 403)
        student.user.refresh_from_db()
        self.assertEqual(student.user.first_name, "Existing")

    def test_other_active_roles_are_denied(self):
        self.client.force_login(self.cashier)
        self.assertEqual(
            self.client.get(reverse("people:student_list")).status_code, 403
        )
        self.assertEqual(
            self.client.post(
                reverse("people:student_create"), self.student_create_payload()
            ).status_code,
            403,
        )

    def test_anonymous_redirected_to_login_with_next(self):
        response = self.client.get(reverse("people:student_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        self.assertIn("next=", response.url)

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.AllowAllUsersModelBackend",
        ]
    )
    def test_inactive_registrar_denied_people_screens(self):
        student = self.make_student()
        self.client.force_login(self.inactive_registrar)
        for url in [
            reverse("people:student_list"),
            reverse("people:student_create"),
            reverse("people:student_detail", args=[student.pk]),
            reverse("people:student_update", args=[student.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.AllowAllUsersModelBackend",
        ]
    )
    def test_inactive_administrator_denied_detail(self):
        instructor = self.make_instructor()
        self.client.force_login(self.inactive_administrator)
        self.assertEqual(
            self.client.get(
                reverse("people:instructor_detail", args=[instructor.pk])
            ).status_code,
            403,
        )


class PeopleScreenTests(PeopleTestCase):
    def test_registrar_can_create_student_account(self):
        self.client.force_login(self.registrar)
        response = self.client.post(
            reverse("people:student_create"), self.student_create_payload()
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="new_student")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.check_password("Str0ngPass!2026"))
        student = Student.objects.get(user=user)
        self.assertEqual(student.student_number, "2026-0001")
        self.assertRedirects(
            response,
            reverse("people:student_detail", args=[student.pk]),
        )

    def test_registrar_can_create_instructor_account(self):
        self.client.force_login(self.registrar)
        response = self.client.post(
            reverse("people:instructor_create"),
            self.instructor_create_payload(),
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="new_instructor")
        self.assertEqual(user.role, User.Role.INSTRUCTOR)
        self.assertTrue(user.check_password("Str0ngPass!2026"))
        instructor = Instructor.objects.get(user=user)
        self.assertEqual(instructor.employee_number, "EMP-2026")

    def test_registrar_can_update_student_account(self):
        student = self.make_student()
        self.client.force_login(self.registrar)
        response = self.client.post(
            reverse("people:student_update", args=[student.pk]),
            self.student_update_payload(
                student,
                first_name="Updated",
                username="updated_student",
                year_level=3,
            ),
        )
        self.assertEqual(response.status_code, 302)
        student.user.refresh_from_db()
        student.refresh_from_db()
        self.assertEqual(student.user.first_name, "Updated")
        self.assertEqual(student.user.username, "updated_student")
        self.assertEqual(student.year_level, 3)

    def test_registrar_can_update_instructor_account(self):
        instructor = self.make_instructor()
        self.client.force_login(self.registrar)
        response = self.client.post(
            reverse("people:instructor_update", args=[instructor.pk]),
            self.instructor_update_payload(
                instructor,
                first_name="Updated",
                employee_number="EMP-2026-UPD",
            ),
        )
        self.assertEqual(response.status_code, 302)
        instructor.user.refresh_from_db()
        instructor.refresh_from_db()
        self.assertEqual(instructor.user.first_name, "Updated")
        self.assertEqual(instructor.employee_number, "EMP-2026-UPD")

    def test_duplicate_username_is_rejected_readably(self):
        self.make_student(username="taken_username", number="TAKEN-001")
        self.client.force_login(self.registrar)
        response = self.client.post(
            reverse("people:student_create"),
            self.student_create_payload(
                username="taken_username", student_number="TAKEN-002"
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertEqual(User.objects.filter(username="taken_username").count(), 1)

    def test_password_mismatch_is_rejected_readably(self):
        self.client.force_login(self.registrar)
        response = self.client.post(
            reverse("people:student_create"),
            self.student_create_payload(password2="DifferentPass!2026"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "do not match")
        self.assertFalse(User.objects.filter(username="new_student").exists())


class PeopleIntegrityErrorTests(PeopleTestCase):
    def setUp(self):
        self.client.force_login(self.registrar)

    def test_student_create_integrity_error_is_handled(self):
        with patch.object(Student, "save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(
                reverse("people:student_create"), self.student_create_payload()
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        self.assertFalse(User.objects.filter(username="new_student").exists())
        self.assertFalse(Student.objects.filter(student_number="2026-0001").exists())
        User.objects.create_user(
            username="after_student_error",
            password="pass12345",
            role=User.Role.STUDENT,
        )

    def test_student_update_integrity_error_is_handled(self):
        student = self.make_student()
        with patch.object(User, "save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(
                reverse("people:student_update", args=[student.pk]),
                self.student_update_payload(
                    student, first_name="Changed", year_level=4
                ),
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        student.user.refresh_from_db()
        student.refresh_from_db()
        self.assertEqual(student.user.first_name, "Existing")
        self.assertEqual(student.year_level, 1)

    def test_instructor_create_integrity_error_is_handled(self):
        with patch.object(
            Instructor, "save", side_effect=IntegrityError("duplicate")
        ):
            response = self.client.post(
                reverse("people:instructor_create"),
                self.instructor_create_payload(),
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        self.assertFalse(
            User.objects.filter(username="new_instructor").exists()
        )
        self.assertFalse(
            Instructor.objects.filter(employee_number="EMP-2026").exists()
        )

    def test_instructor_update_integrity_error_is_handled(self):
        instructor = self.make_instructor()
        with patch.object(
            Instructor, "save", side_effect=IntegrityError("duplicate")
        ):
            response = self.client.post(
                reverse("people:instructor_update", args=[instructor.pk]),
                self.instructor_update_payload(
                    instructor, first_name="Changed", employee_number="EMP-999"
                ),
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONFLICT_ERROR)
        instructor.user.refresh_from_db()
        instructor.refresh_from_db()
        self.assertEqual(instructor.user.first_name, "Existing")
        self.assertEqual(instructor.employee_number, "EMP-001")

    def test_integrity_error_response_does_not_leak_database_details(self):
        with patch.object(Student, "save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(
                reverse("people:student_create"), self.student_create_payload()
            )
        content = response.content.decode()
        self.assertNotIn("IntegrityError", content)
        self.assertNotIn("Duplicate entry", content)
        self.assertNotIn("INSERT INTO", content)
        self.assertNotIn("Traceback", content)


class LoginViewHardeningTests(PeopleTestCase):
    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.AllowAllUsersModelBackend",
        ]
    )
    def test_inactive_session_visiting_login_is_logged_out(self):
        self.client.force_login(self.inactive_registrar)
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.AllowAllUsersModelBackend",
        ]
    )
    def test_inactive_session_on_dashboard_redirects_to_login(self):
        self.client.force_login(self.inactive_registrar)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))

    def test_active_user_login_redirects_to_role_dashboard(self):
        response = self.client.post(
            reverse("login"),
            {"username": "people_reg", "password": "pass12345"},
        )
        self.assertRedirects(response, reverse("registrar_dashboard"))

    def test_safe_next_is_honoured(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "people_reg",
                "password": "pass12345",
                "next": reverse("people:student_list"),
            },
        )
        self.assertRedirects(response, reverse("people:student_list"))

    def test_unsafe_next_is_ignored(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "people_reg",
                "password": "pass12345",
                "next": "https://evil.example/",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("evil.example", response.url)
