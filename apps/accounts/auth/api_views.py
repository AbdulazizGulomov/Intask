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
def verify_otp_view(request):
    print("===== VERIFY OTP DEBUG =====")
    print("request.data =", request.data)
    print("raw phone =", request.data.get("phone"))
    print("raw code =", request.data.get("code"))
    print("raw next =", request.data.get("next"))

    s = VerifyOtpSerializer(data=request.data)
    if not s.is_valid():
        print("SERIALIZER ERRORS =", s.errors)
        print("============================")
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = normalize_phone(s.validated_data["phone"])
    code = s.validated_data["code"]

    print("normalized phone =", phone)
    print("validated code =", code)

    next_url = request.data.get("next") or "/"

    otp_ok = verify_otp(phone, code)
    print("verify_otp result =", otp_ok)

    if not otp_ok:
        print("FAIL: Invalid or expired code")
        print("============================")
        return Response({"detail": "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST)

    user, created = User.objects.get_or_create(
        phone=phone,
        defaults={"role": request.session.get("user_role") or "worker", "is_active": True},
    )

    print("user =", user.id, "created =", created)

    if user.is_staff:
        print("FAIL: admin tried OTP login")
        print("============================")
        return Response({"detail": "Admins cannot login via OTP"}, status=status.HTTP_403_FORBIDDEN)

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    refresh = RefreshToken.for_user(user)

    gate_url = reverse("accounts:after_otp_redirect")
    gate_url = gate_url + "?" + urlencode({"next": next_url})

    print("SUCCESS")
    print("============================")

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