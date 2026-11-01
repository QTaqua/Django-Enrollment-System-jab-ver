from django.urls import path

from accounts import people_views

app_name = "people"

urlpatterns = [
    path("students/", people_views.StudentListView.as_view(), name="student_list"),
    path("students/add/", people_views.StudentCreateView.as_view(), name="student_create"),
    path("students/<int:pk>/", people_views.StudentDetailView.as_view(), name="student_detail"),
    path("students/<int:pk>/edit/", people_views.StudentUpdateView.as_view(), name="student_update"),
    path("instructors/", people_views.InstructorListView.as_view(), name="instructor_list"),
    path("instructors/add/", people_views.InstructorCreateView.as_view(), name="instructor_create"),
    path("instructors/<int:pk>/", people_views.InstructorDetailView.as_view(), name="instructor_detail"),
    path("instructors/<int:pk>/edit/", people_views.InstructorUpdateView.as_view(), name="instructor_update"),
]
