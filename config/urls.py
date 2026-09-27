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
    JobApplicationsAPIView,
    ApplicationAcceptAPIView,
    ApplicationRejectAPIView,
)
from apps.jobs.geocode import ReverseGeocodeAPIView
from apps.jobs.views import mobile_map_picker
from apps.accounts.views import (
    me as me_view,
    become_employer as become_employer_view,
    accept_terms as accept_terms_view,
)
from apps.moderation.api import (
    ReportCreateAPIView,
    BlockListCreateAPIView,
    BlockDeleteAPIView,
)

urlpatterns = [
    path("api/dashboard/", include("apps.accounts.dashboard.urls")),  # operator dashboard API
    path("", include("apps.accounts.urls")),  # accounts pages
    path("jobs/", include(("apps.jobs.urls", "jobs"), namespace="jobs")),  # ✅ register jobs namespace

    path("api/me/", me_view, name="api_me"),  # GET + PATCH worker profile
    path("api/me/become-employer/", become_employer_view, name="api_become_employer"),
    path("api/me/accept-terms/", accept_terms_view, name="api_accept_terms"),

    # UGC safety (App Store Guideline 1.2): report + block.
    path("api/reports/", ReportCreateAPIView.as_view(), name="api_report_create"),
    path("api/blocks/", BlockListCreateAPIView.as_view(), name="api_blocks"),
    path("api/blocks/<int:user_id>/", BlockDeleteAPIView.as_view(), name="api_block_delete"),

    path("api/jobs/", JobListAPIView.as_view(), name="api_job_list"),
    path("api/jobs/create/", JobCreateAPIView.as_view(), name="api_job_create"),
    path("api/jobs/<int:pk>/", JobDetailAPIView.as_view(), name="api_job_detail"),
    path("api/jobs/<int:pk>/apply/", JobApplyAPIView.as_view(), name="api_job_apply"),

    # Employer side (mobile 4d-5 / 9c): applicants of an own job + decisions.
    path("api/jobs/<int:pk>/applications/", JobApplicationsAPIView.as_view(), name="api_job_applications"),
    path("api/applications/<int:pk>/accept/", ApplicationAcceptAPIView.as_view(), name="api_application_accept"),
    path("api/applications/<int:pk>/reject/", ApplicationRejectAPIView.as_view(), name="api_application_reject"),

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
