from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode
from django.contrib.auth import login

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.auth.serializers import SendOtpSerializer, VerifyOtpSerializer
from .otp import send_otp, verify_otp, normalize_phone
from apps.accounts.models import User


@api_view(["POST"])
def send_otp_view(request):
    s = SendOtpSerializer(data=request.data)
    s.is_valid(raise_exception=True)

    phone = normalize_phone(s.validated_data["phone"])
    code = send_otp(phone)

    data = {"message": "OTP sent", "phone": phone}
    if getattr(settings, "OTP_DEBUG_RETURN_CODE", False):
        data["debug_code"] = code  # DEV only

    return Response(data, status=status.HTTP_200_OK)


@api_view(["POST"])
def verify_otp_view(request):
    s = VerifyOtpSerializer(data=request.data)
    s.is_valid(raise_exception=True)

    phone = normalize_phone(s.validated_data["phone"])
    code = s.validated_data["code"]

    next_url = request.data.get("next") or "/"  # where user wanted to go

    if not verify_otp(phone, code):
        return Response({"detail": "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST)

    user, created = User.objects.get_or_create(
        phone=phone,
        defaults={"role": request.session.get("user_role") or "worker", "is_active": True},
    )

    # block admin OTP
    if user.is_staff:
        return Response({"detail": "Admins cannot login via OTP"}, status=status.HTTP_403_FORBIDDEN)

    # ✅ IMPORTANT: create Django session login (so /after-otp/ sees request.user)

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    # JWT tokens (optional for later mobile/API use)
    refresh = RefreshToken.for_user(user)

    # ✅ IMPORTANT: always send user to gate after otp
    gate_url = reverse("accounts:after_otp_redirect")
    gate_url = gate_url + "?" + urlencode({"next": next_url})

    return Response(
        {
            "message": "OTP verified",
            "user_id": user.id,
            "phone": user.phone,
            "created": created,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "next": gate_url,  # ✅ redirect here
        },
        status=status.HTTP_200_OK,
    )
