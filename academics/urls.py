from django.urls import path

from academics import views

app_name = "academics"

urlpatterns = [
    path("colleges/", views.CollegeListView.as_view(), name="college_list"),
    path("colleges/add/", views.CollegeCreateView.as_view(), name="college_create"),
    path("colleges/<int:pk>/", views.CollegeDetailView.as_view(), name="college_detail"),
    path("colleges/<int:pk>/edit/", views.CollegeUpdateView.as_view(), name="college_update"),
    path("programs/", views.ProgramListView.as_view(), name="program_list"),
    path("programs/add/", views.ProgramCreateView.as_view(), name="program_create"),
    path("programs/<int:pk>/", views.ProgramDetailView.as_view(), name="program_detail"),
    path("programs/<int:pk>/edit/", views.ProgramUpdateView.as_view(), name="program_update"),
    path("curricula/", views.CurriculumListView.as_view(), name="curriculum_list"),
    path("curricula/add/", views.CurriculumCreateView.as_view(), name="curriculum_create"),
    path("curricula/<int:pk>/", views.CurriculumDetailView.as_view(), name="curriculum_detail"),
    path("curricula/<int:pk>/edit/", views.CurriculumUpdateView.as_view(), name="curriculum_update"),
    path("courses/", views.CourseListView.as_view(), name="course_list"),
    path("courses/add/", views.CourseCreateView.as_view(), name="course_create"),
    path("courses/<int:pk>/", views.CourseDetailView.as_view(), name="course_detail"),
    path("courses/<int:pk>/edit/", views.CourseUpdateView.as_view(), name="course_update"),
    path("curriculum-courses/", views.CurriculumCourseListView.as_view(), name="curriculum_course_list"),
    path("curriculum-courses/add/", views.CurriculumCourseCreateView.as_view(), name="curriculum_course_create"),
    path("curriculum-courses/<int:pk>/", views.CurriculumCourseDetailView.as_view(), name="curriculum_course_detail"),
    path("curriculum-courses/<int:pk>/edit/", views.CurriculumCourseUpdateView.as_view(), name="curriculum_course_update"),
    path("course-prerequisites/", views.CoursePrerequisiteListView.as_view(), name="course_prerequisite_list"),
    path("course-prerequisites/add/", views.CoursePrerequisiteCreateView.as_view(), name="course_prerequisite_create"),
    path("course-prerequisites/<int:pk>/", views.CoursePrerequisiteDetailView.as_view(), name="course_prerequisite_detail"),
    path("course-prerequisites/<int:pk>/edit/", views.CoursePrerequisiteUpdateView.as_view(), name="course_prerequisite_update"),
    path("academic-terms/", views.AcademicTermListView.as_view(), name="academic_term_list"),
    path("academic-terms/add/", views.AcademicTermCreateView.as_view(), name="academic_term_create"),
    path("academic-terms/<int:pk>/", views.AcademicTermDetailView.as_view(), name="academic_term_detail"),
    path("academic-terms/<int:pk>/edit/", views.AcademicTermUpdateView.as_view(), name="academic_term_update"),
]
