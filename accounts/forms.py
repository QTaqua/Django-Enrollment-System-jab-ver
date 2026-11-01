"""Forms for Registrar-managed student and instructor accounts."""

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from accounts.models import User
from academics.models import Curriculum, Instructor, Student

USER_FIELD_NAMES = (
    "first_name",
    "last_name",
    "middle_name",
    "email",
    "phone",
    "address",
)


class BootstrapFormMixin:
    """Apply Bootstrap classes to rendered widgets without changing layouts."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class _AccountFormBase(BootstrapFormMixin, forms.Form):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    middle_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    phone = forms.CharField(max_length=30, required=False)
    address = forms.CharField(max_length=255, required=False, widget=forms.Textarea(attrs={"rows": 2}))
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"]
        queryset = User.objects.filter(username=username)
        if self._excluded_user_id() is not None:
            queryset = queryset.exclude(pk=self._excluded_user_id())
        if queryset.exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def _excluded_user_id(self):
        return None

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if not password1 and not password2:
            # Account forms mark both fields as required at field level.
            # Profile forms allow both to be blank (password unchanged).
            return cleaned
        if not password1 or not password2:
            self.add_error(
                "password2",
                "Enter and confirm the new password, or leave both blank.",
            )
        elif password1 != password2:
            self.add_error("password2", "The two password fields do not match.")
        else:
            candidate = self._candidate_user(cleaned)
            try:
                validate_password(password1, user=candidate)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

    def _candidate_user(self, cleaned):
        return User(
            username=cleaned.get("username", ""),
            first_name=cleaned.get("first_name", ""),
            last_name=cleaned.get("last_name", ""),
            email=cleaned.get("email", ""),
        )

    def user_fields(self):
        return {
            name: self.cleaned_data.get(name) or ""
            for name in USER_FIELD_NAMES
        }


class _ProfileFormBase(_AccountFormBase):
    password1 = forms.CharField(
        label="New password", widget=forms.PasswordInput, required=False
    )
    password2 = forms.CharField(
        label="Confirm new password", widget=forms.PasswordInput, required=False
    )

    def __init__(self, *args, student=None, instructor=None, **kwargs):
        self.student = student
        self.instructor = instructor
        super().__init__(*args, **kwargs)

    def _excluded_user_id(self):
        profile = self.student or self.instructor
        return profile.user_id if profile is not None else None

    def user_fields(self):
        fields = super().user_fields()
        fields["username"] = self.cleaned_data["username"]
        return fields

    def _candidate_user(self, cleaned):
        profile = self.student or self.instructor
        return User(
            pk=profile.user_id if profile is not None else None,
            username=cleaned.get("username", ""),
            first_name=cleaned.get("first_name", ""),
            last_name=cleaned.get("last_name", ""),
            email=cleaned.get("email", ""),
        )


class StudentAccountForm(_AccountFormBase):
    student_number = forms.CharField(max_length=30)
    curriculum = forms.ModelChoiceField(
        queryset=Curriculum.objects.select_related("program").order_by(
            "program__program_code", "curriculum_code"
        )
    )
    year_level = forms.IntegerField(min_value=1)

    def clean_student_number(self):
        student_number = self.cleaned_data["student_number"]
        if Student.objects.filter(student_number=student_number).exists():
            raise ValidationError("A student with that student number already exists.")
        return student_number


class StudentProfileForm(_ProfileFormBase):
    student_number = forms.CharField(max_length=30)
    curriculum = forms.ModelChoiceField(
        queryset=Curriculum.objects.select_related("program").order_by(
            "program__program_code", "curriculum_code"
        )
    )
    year_level = forms.IntegerField(min_value=1)

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, student=student, **kwargs)
        if student is not None and not self.is_bound:
            user = student.user
            self.fields["username"].initial = user.username
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["middle_name"].initial = user.middle_name
            self.fields["email"].initial = user.email
            self.fields["phone"].initial = user.phone
            self.fields["address"].initial = user.address
            self.fields["student_number"].initial = student.student_number
            self.fields["curriculum"].initial = student.curriculum_id
            self.fields["year_level"].initial = student.year_level

    def clean_student_number(self):
        student_number = self.cleaned_data["student_number"]
        queryset = Student.objects.filter(student_number=student_number)
        if self.student is not None:
            queryset = queryset.exclude(pk=self.student.pk)
        if queryset.exists():
            raise ValidationError("A student with that student number already exists.")
        return student_number

    def profile_fields(self):
        return {
            "student_number": self.cleaned_data["student_number"],
            "curriculum": self.cleaned_data["curriculum"],
            "year_level": self.cleaned_data["year_level"],
        }


class InstructorAccountForm(_AccountFormBase):
    employee_number = forms.CharField(max_length=30)

    def clean_employee_number(self):
        employee_number = self.cleaned_data["employee_number"]
        if Instructor.objects.filter(employee_number=employee_number).exists():
            raise ValidationError(
                "An instructor with that employee number already exists."
            )
        return employee_number


class InstructorProfileForm(_ProfileFormBase):
    employee_number = forms.CharField(max_length=30)

    def __init__(self, *args, instructor=None, **kwargs):
        super().__init__(*args, instructor=instructor, **kwargs)
        if instructor is not None and not self.is_bound:
            user = instructor.user
            self.fields["username"].initial = user.username
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["middle_name"].initial = user.middle_name
            self.fields["email"].initial = user.email
            self.fields["phone"].initial = user.phone
            self.fields["address"].initial = user.address
            self.fields["employee_number"].initial = instructor.employee_number

    def clean_employee_number(self):
        employee_number = self.cleaned_data["employee_number"]
        queryset = Instructor.objects.filter(employee_number=employee_number)
        if self.instructor is not None:
            queryset = queryset.exclude(pk=self.instructor.pk)
        if queryset.exists():
            raise ValidationError(
                "An instructor with that employee number already exists."
            )
        return employee_number

    def profile_fields(self):
        return {"employee_number": self.cleaned_data["employee_number"]}
