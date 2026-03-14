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

import logging

logger = logging.getLogger(__name__)


@api_view(["POST"])
def send_otp_view(request):
    logger.info("SEND OTP REQUEST: %s", request.data)

    s = SendOtpSerializer(data=request.data)

    if not s.is_valid():
        logger.error("SEND OTP SERIALIZER ERROR: %s", s.errors)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = normalize_phone(s.validated_data["phone"])

    logger.info("Normalized phone: %s", phone)

    code = send_otp(phone)

    data = {
        "message": "OTP sent",
        "phone": phone,
    }

    if getattr(settings, "OTP_DEBUG_RETURN_CODE", False):
        data["debug_code"] = code

    logger.info("OTP sent successfully")

    return Response(data, status=status.HTTP_200_OK)


@api_view(["POST"])
def verify_otp_view(request):
    logger.info("VERIFY OTP REQUEST: %s", request.data)

    s = VerifyOtpSerializer(data=request.data)

    if not s.is_valid():
        logger.error("VERIFY OTP SERIALIZER ERROR: %s", s.errors)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = normalize_phone(s.validated_data["phone"])
    code = s.validated_data["code"]

    logger.info("Phone: %s Code: %s", phone, code)

    next_url = request.data.get("next") or "/"

    if not verify_otp(phone, code):
        logger.warning("Invalid OTP for phone: %s", phone)
        return Response(
            {"detail": "Invalid or expired code"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user, created = User.objects.get_or_create(
        phone=phone,
        defaults={
            "role": request.session.get("user_role") or "worker",
            "is_active": True,
        },
    )

    if user.is_staff:
        logger.warning("Admin tried OTP login: %s", phone)
        return Response(
            {"detail": "Admins cannot login via OTP"},
            status=status.HTTP_403_FORBIDDEN,
        )

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    refresh = RefreshToken.for_user(user)

    gate_url = reverse("accounts:after_otp_redirect")
    gate_url = gate_url + "?" + urlencode({"next": next_url})

    logger.info("OTP login success user=%s", user.id)

    return Response(
        {
            "message": "OTP verified",
            "user_id": user.id,
            "phone": user.phone,
            "created": created,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "next": gate_url,
        },
        status=status.HTTP_200_OK,
    )