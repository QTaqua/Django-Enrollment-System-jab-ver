from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import views

urlpatterns = [
    path("login/", views.RoleAwareLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),
    path("dashboard/instructor/", views.instructor_dashboard, name="instructor_dashboard"),
    path("dashboard/cashier/", views.cashier_dashboard, name="cashier_dashboard"),
    path("dashboard/registrar/", views.registrar_dashboard, name="registrar_dashboard"),
    path("dashboard/administrator/", views.administrator_dashboard, name="administrator_dashboard"),
]
