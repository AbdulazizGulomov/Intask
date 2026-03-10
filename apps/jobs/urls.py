from django.urls import path
from . import views

app_name = "jobs"

urlpatterns = [
    path("employer/jobs/create/", views.employer_job_create, name="employer_job_create"),
    path("<int:pk>/", views.job_detail, name="detail"),
]
