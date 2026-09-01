# config/urls.py
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

from apps.jobs.api import (
    JobListAPIView,
    JobDetailAPIView,
    JobApplyAPIView,
    JobCreateAPIView,
    MyJobsAPIView,
    MyApplicationsAPIView,
    ProfessionListAPIView,
)
from apps.jobs.geocode import ReverseGeocodeAPIView
from apps.jobs.views import mobile_map_picker
from apps.accounts.views import me as me_view, become_employer as become_employer_view

urlpatterns = [
    path("api/dashboard/", include("apps.accounts.dashboard.urls")),  # operator dashboard API
    path("", include("apps.accounts.urls")),  # accounts pages
    path("jobs/", include(("apps.jobs.urls", "jobs"), namespace="jobs")),  # ✅ register jobs namespace

    path("api/me/", me_view, name="api_me"),  # GET + PATCH worker profile
    path("api/me/become-employer/", become_employer_view, name="api_become_employer"),

    path("api/jobs/", JobListAPIView.as_view(), name="api_job_list"),
    path("api/jobs/create/", JobCreateAPIView.as_view(), name="api_job_create"),
    path("api/jobs/<int:pk>/", JobDetailAPIView.as_view(), name="api_job_detail"),
    path("api/jobs/<int:pk>/apply/", JobApplyAPIView.as_view(), name="api_job_apply"),

    path("api/my-jobs/", MyJobsAPIView.as_view(), name="api_my_jobs"),
    path("api/my-applications/", MyApplicationsAPIView.as_view(), name="api_my_applications"),

    path("api/professions/", ProfessionListAPIView.as_view(), name="api_professions"),

    # Mobile post flow: reverse geocoding + WebView map picker. Both must stay
    # at these exact unprefixed paths (no i18n_patterns in this URLconf).
    path("api/geocode/reverse/", ReverseGeocodeAPIView.as_view(), name="api_geocode_reverse"),
    path("m/map-picker/", mobile_map_picker, name="mobile_map_picker"),

    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
]

#
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
