from django.urls import path

from accounts import report_views

app_name = "reports"

urlpatterns = [
    path("", report_views.reports_index, name="index"),
    path("enrolled/", report_views.enrolled_report, name="enrolled"),
    path("semester/", report_views.semester_report, name="semester"),
    path("collection/", report_views.collection_report, name="collection"),
]
