# config/urls.py
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

from apps.jobs.api import JobListAPIView, JobDetailAPIView, JobApplyAPIView

urlpatterns = [
    path("api/dashboard/", include("apps.accounts.dashboard.urls")),  # operator dashboard API
    path("", include("apps.accounts.urls")),  # accounts pages
    path("jobs/", include(("apps.jobs.urls", "jobs"), namespace="jobs")),  # ✅ register jobs namespace

    path("api/jobs/", JobListAPIView.as_view(), name="api_job_list"),
    path("api/jobs/<int:pk>/", JobDetailAPIView.as_view(), name="api_job_detail"),
    path("api/jobs/<int:pk>/apply/", JobApplyAPIView.as_view(), name="api_job_apply"),

    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
]

#
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
