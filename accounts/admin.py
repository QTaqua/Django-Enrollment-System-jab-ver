from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.admin_site import ads_admin_site
from accounts.models import User
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
from finance.models import (
    Adjustment,
    Assessment,
    AssessmentLine,
    AssessmentVersion,
    FeeRule,
    FinanceAuditLog,
    FinancePolicy,
    Payment,
    PaymentAllocation,
    Reconciliation,
    ScholarshipAward,
)
from scheduling.models import Room, Section


class ReadOnlyAdmin(admin.ModelAdmin):
    """Read-only admin for models that must not be mutated via Django Admin."""

    actions = []

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        fields = [f.name for f in self.model._meta.fields]
        m2m = [f.name for f in self.model._meta.many_to_many]
        return fields + m2m


@admin.register(User, site=ads_admin_site)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = (
        "username",
        "email",
        "last_name",
        "first_name",
        "role",
        "is_staff",
        "is_active",
        "is_superuser",
    )
    list_filter = ("role", "is_staff", "is_active", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    actions = []

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        extra = [
            ("Role", {"fields": ("role",)}),
            (
                "Contact",
                {"fields": ("middle_name", "phone", "address")},
            ),
        ]
        for fieldset in extra:
            name = fieldset[0]
            if not any(fs[0] == name for fs in fieldsets):
                fieldsets.append(fieldset)
        return fieldsets

    def get_add_fieldsets(self, request):
        add_fieldsets = list(super().get_add_fieldsets(request))
        extra = [
            ("Role", {"fields": ("role",)}),
            (
                "Contact",
                {"fields": ("middle_name", "phone", "address")},
            ),
        ]
        for fieldset in extra:
            name = fieldset[0]
            if not any(fs[0] == name for fs in add_fieldsets):
                add_fieldsets.append(fieldset)
        return add_fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if "is_superuser" not in readonly:
            readonly.append("is_superuser")
        if obj is not None and obj.pk == request.user.pk:
            for field in [
                "role",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ]:
                if field not in readonly:
                    readonly.append(field)
        return readonly

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is not None and obj.pk == request.user.pk:
            for field in [
                "role",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ]:
                if field in form.base_fields:
                    form.base_fields[field].disabled = True
        return form

    def save_model(self, request, obj, form, change):
        if change and obj.pk == request.user.pk:
            original = User.objects.get(pk=obj.pk)
            obj.role = original.role
            obj.is_staff = original.is_staff
            obj.is_superuser = original.is_superuser
            obj.groups.set(original.groups.all())
            obj.user_permissions.set(original.user_permissions.all())
        if obj.is_superuser and not request.user.is_superuser:
            obj.is_superuser = False
        super().save_model(request, obj, form, change)


@admin.register(College, site=ads_admin_site)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ("college_code", "name", "is_active")
    search_fields = ("college_code", "name")
    list_filter = ("is_active",)
    actions = []

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Program, site=ads_admin_site)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("program_code", "name", "college", "is_active")
    search_fields = ("program_code", "name")
    list_filter = ("college", "is_active")
    actions = []

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Curriculum, site=ads_admin_site)
class CurriculumAdmin(admin.ModelAdmin):
    list_display = ("curriculum_code", "program", "effective_year", "is_active")
    search_fields = ("curriculum_code",)
    list_filter = ("program", "effective_year", "is_active")
    actions = []

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Course, site=ads_admin_site)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("course_code", "title", "units", "is_active")
    search_fields = ("course_code", "title")
    list_filter = ("is_active",)
    actions = []

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CurriculumCourse, site=ads_admin_site)
class CurriculumCourseAdmin(admin.ModelAdmin):
    list_display = (
        "curriculum",
        "course",
        "year_level",
        "recommended_semester",
        "course_category",
    )
    list_filter = ("curriculum", "year_level", "recommended_semester", "course_category")
    actions = []

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CoursePrerequisite, site=ads_admin_site)
class CoursePrerequisiteAdmin(admin.ModelAdmin):
    list_display = ("course", "prerequisite_course")
    search_fields = ("course__course_code", "prerequisite_course__course_code")
    actions = []

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AcademicTerm, site=ads_admin_site)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = (
        "academic_year",
        "semester_number",
        "start_date",
        "end_date",
        "enrollment_open",
    )
    list_filter = ("academic_year", "semester_number", "enrollment_open")
    actions = []

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Room, site=ads_admin_site)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_code", "name", "building", "capacity", "is_active")
    search_fields = ("room_code", "name", "building")
    list_filter = ("is_active",)
    actions = []

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FeeRule, site=ads_admin_site)
class FeeRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "scope", "computation", "amount",
                    "course", "program", "is_active", "is_demo")
    list_filter = ("category", "scope", "computation", "is_active", "is_demo")
    search_fields = ("name",)
    actions = []

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FinancePolicy, site=ads_admin_site)
class FinancePolicyAdmin(admin.ModelAdmin):
    list_display = ("previous_term_balance", "overpayment_becomes_credit",
                    "credit_application_requires_approval",
                    "refund_requires_approval", "updated_at")
    actions = []

    def has_delete_permission(self, request, obj=None):
        return False


# Read-only finance ledger / audit models (managed through finance services/views)
ads_admin_site.register(AssessmentVersion, ReadOnlyAdmin)
ads_admin_site.register(AssessmentLine, ReadOnlyAdmin)
ads_admin_site.register(PaymentAllocation, ReadOnlyAdmin)
ads_admin_site.register(Adjustment, ReadOnlyAdmin)
ads_admin_site.register(ScholarshipAward, ReadOnlyAdmin)
ads_admin_site.register(Reconciliation, ReadOnlyAdmin)
ads_admin_site.register(FinanceAuditLog, ReadOnlyAdmin)

# Read-only models
ads_admin_site.register(Student, ReadOnlyAdmin)
ads_admin_site.register(Instructor, ReadOnlyAdmin)
ads_admin_site.register(Section, ReadOnlyAdmin)
ads_admin_site.register(Enrollment, ReadOnlyAdmin)
ads_admin_site.register(EnrollmentDetail, ReadOnlyAdmin)
ads_admin_site.register(Assessment, ReadOnlyAdmin)
ads_admin_site.register(Payment, ReadOnlyAdmin)
