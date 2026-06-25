from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils.http import urlencode, url_has_allowed_host_and_scheme
from django.contrib.auth import login

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.auth.serializers import SendOtpSerializer, VerifyOtpSerializer, is_valid_uz_phone
from .otp import send_otp, verify_otp, normalize_phone
from apps.accounts.models import User


def _incr_with_ttl(key, ttl):
    """Increment a counter, seeding it with `ttl` on first use.

    cache.incr raises ValueError when the key is absent; both LocMemCache and
    Redis preserve the original expiry across subsequent increments, so the
    window does not slide.
    """
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=ttl)
        return 1


def _client_ip(request):
    """Client IP behind Nginx: leftmost X-Forwarded-For hop, else REMOTE_ADDR.

    XFF is client-spoofable, but Nginx is configured to set it, so the
    leftmost entry is the original client. REMOTE_ADDR is the fallback.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _check_send_throttle(phone, ip):
    """Enforce send-OTP rate limits. Returns (retry_after, detail) when
    throttled, else (None, None). Limits are settings-overridable."""
    # LOCAL DEV ONLY — never active in production (DEBUG=False on server).
    if settings.DEBUG:
        return None, None

    cooldown = getattr(settings, "OTP_SEND_COOLDOWN_SECONDS", 60)
    phone_per_hour = getattr(settings, "OTP_SEND_MAX_PER_HOUR", 5)
    ip_per_hour = getattr(settings, "OTP_SEND_MAX_PER_HOUR_PER_IP", 20)

    # 1) Per-phone cooldown — blocks rapid re-sends before touching hourly budgets.
    if cache.get(f"otp_send_cooldown:{phone}"):
        return cooldown, "Please wait before requesting another code."

    # 2) Per-phone hourly cap.
    if _incr_with_ttl(f"otp_send_hourly:{phone}", 3600) > phone_per_hour:
        return 3600, "Too many code requests for this number. Try again later."

    # 3) Per-IP hourly cap — stops one client hammering many numbers.
    if ip and _incr_with_ttl(f"otp_send_ip:{ip}", 3600) > ip_per_hour:
        return 3600, "Too many requests from your network. Try again later."

    # Allowed → start the per-phone cooldown window.
    cache.set(f"otp_send_cooldown:{phone}", 1, timeout=cooldown)
    return None, None


@api_view(["POST"])
def send_otp_view(request):
    s = SendOtpSerializer(data=request.data)
    s.is_valid(raise_exception=True)

    phone = normalize_phone(s.validated_data["phone"])

    # Defense in depth: never write a cache/throttle key or attempt an SMS for a
    # non-valid number, even if the serializer path is ever bypassed.
    if not is_valid_uz_phone(phone):
        return Response({"detail": "Enter a valid phone number."}, status=status.HTTP_400_BAD_REQUEST)

    retry_after, detail = _check_send_throttle(phone, _client_ip(request))
    if detail:
        resp = Response({"detail": detail}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        if retry_after:
            resp["Retry-After"] = str(retry_after)
        return resp

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

    # Only honor local, same-host paths; anything external falls back to "/".
    if not url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()},
            require_https=request.is_secure()):
        next_url = "/"

    ok, err = verify_otp(phone, code)
    if not ok:
        return Response({"detail": err or "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST)

    user, created = User.objects.get_or_create(
        phone=phone,
        defaults={"role": request.session.get("user_role") or "", "is_active": True},
    )

    # block admin OTP
    if user.is_staff:
        return Response({"detail": "Admins cannot login via OTP"}, status=status.HTTP_403_FORBIDDEN)

    # Change 1: persist the FIRST role only. If this account has no role yet and a
    # role was chosen at /role/ (stored in session), assign it. Never override an
    # existing non-empty role (no role-flipping — that is a separate decision).
    if not user.role:
        session_role = request.session.get("user_role")
        if session_role:
            user.role = session_role
            user.save(update_fields=["role"])

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
