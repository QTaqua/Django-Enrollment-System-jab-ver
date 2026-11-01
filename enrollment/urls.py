from django.urls import path

from enrollment import views

app_name = "enrollment"

urlpatterns = [
    path("enrollments/", views.EnrollmentListView.as_view(), name="enrollment_list"),
    path(
        "enrollments/add/",
        views.EnrollmentCreateView.as_view(),
        name="enrollment_create",
    ),
    path(
        "enrollments/<int:pk>/",
        views.EnrollmentDetailView.as_view(),
        name="enrollment_detail",
    ),
    path(
        "enrollments/<int:pk>/add-section/",
        views.EnrollmentAddSectionView.as_view(),
        name="enrollment_add_section",
    ),
    path(
        "enrollments/<int:pk>/confirm/",
        views.EnrollmentConfirmView.as_view(),
        name="enrollment_confirm",
    ),
    path(
        "enrollments/<int:pk>/sections/<int:detail_pk>/remove/",
        views.EnrollmentRemoveSectionView.as_view(),
        name="enrollment_remove_section",
    ),
    path(
        "my-enrollments/",
        views.MyEnrollmentListView.as_view(),
        name="my_enrollment_list",
    ),
    path(
        "my-enrollments/<int:pk>/",
        views.MyEnrollmentDetailView.as_view(),
        name="my_enrollment_detail",
    ),
]
