from django.urls import path
from apps.accounts.auth.api_views import send_otp_view, verify_otp_view

urlpatterns = [
    path("send-otp/", send_otp_view, name="send_otp"),
    path("verify-otp/", verify_otp_view, name="verify_otp"),
]