# apps/accounts/urls.py
from django.urls import path
from apps.accounts import views
from apps.jobs import views as job_views

from .auth.api_views import send_otp_view, verify_otp_view
from .views import me
from rest_framework_simplejwt.views import TokenRefreshView

app_name = "accounts"

urlpatterns = [

    # Role & start
    path("", views.role_select, name="role_select"),
    path("choose-role/<str:role>/", views.choose_role, name="choose_role"),
    path("after-otp/", views.after_otp_redirect, name="after_otp_redirect"),

    # OTP UI (WEB)
    path("otp/", views.otp_login, name="otp"),
    path("otp/verify/", views.otp_verify_web, name="otp_verify_web"),

    # Worker pages
    path("worker/", views.worker_home, name="worker_home"),
    path("worker/register/", views.worker_register, name="worker_register"),

    # ✅ FIXED APPLY ROUTE
    path("worker/apply/<int:job_id>/", views.worker_apply, name="worker_apply"),

    # Job detail
    path("worker/job/<int:job_id>/", job_views.worker_job_detail, name="worker_job_detail"),

    # Employer pages
    path("employer/", views.employer_home, name="employer_home"),
    path("employer/workers/", views.workers_base, name="workers_base"),

    # Logout
    path("logout/", views.logout_view, name="logout"),

    # Auth (API)
    path("auth/send-otp/", send_otp_view, name="api_send_otp"),
    path("auth/verify-otp/", verify_otp_view, name="api_verify_otp"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Profile (API)
    path("me/", me, name="me"),
]