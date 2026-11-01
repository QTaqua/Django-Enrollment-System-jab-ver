from django.urls import path

from scheduling import views

app_name = "scheduling"

urlpatterns = [
    path("", views.SectionListView.as_view(), name="section_list"),
    path("add/", views.SectionCreateView.as_view(), name="section_create"),
    path("<int:pk>/", views.SectionDetailView.as_view(), name="section_detail"),
    path("<int:pk>/edit/", views.SectionUpdateView.as_view(), name="section_update"),
]
