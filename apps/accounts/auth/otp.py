# apps/accounts/auth/otp.py
import hashlib
import hmac
import logging
import re
import secrets

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """
    Normalize to format: +998901234567
    Accepts:
    901234567
    998901234567
    +998 90 123 45 67
    """
    p = (phone or "").strip()
    digits = re.sub(r"\D", "", p)

    if len(digits) == 9:
        digits = "998" + digits

    if digits.startswith("998"):
        return "+" + digits

    return "+" + digits if digits else ""


def generate_otp_code() -> str:
    # Cryptographically secure 6-digit code (000000–999999), always zero-padded.
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_code(code: str) -> str:
    """HMAC-SHA256 of the code (keyed with SECRET_KEY) → 64-char hex digest.

    Only the hash is stored in the cache; the plaintext OTP is never persisted.
    """
    return hmac.new(
        settings.SECRET_KEY.encode(),
        (code or "").strip().encode(),
        hashlib.sha256,
    ).hexdigest()


def _play_review_config() -> tuple[list[str], str]:
    """Google Play reviewer bypass: (normalized_phones, fixed_code).

    Play reviewers cannot receive our Eskiz SMS, so the reviewer phone(s)
    accept a fixed code — in production, DEBUG-independent. PLAY_REVIEW_PHONE
    may hold several numbers (e.g. one worker + one employer reviewer); all
    share the same code. Both values come from the server .env only (public
    repo — never hardcode them). Returns ([], "") — bypass fully disabled —
    unless BOTH are set. Never log any of these values.
    """
    raw = getattr(settings, "PLAY_REVIEW_PHONE", None) or []
    if isinstance(raw, str):  # tolerate a plain single-number string
        raw = [raw]
    code = str(getattr(settings, "PLAY_REVIEW_OTP", "") or "")
    if not raw or not code:
        return [], ""
    return [p for p in (normalize_phone(x) for x in raw) if p], code


def otp_cache_key(phone: str) -> str:
    return f"otp:{phone}"


def otp_attempts_key(phone: str) -> str:
    return f"otp_attempts:{phone}"


MAX_OTP_ATTEMPTS = 5


def get_eskiz_token():
    """Retrieve or refresh Eskiz API token."""
    token = cache.get("eskiz_auth_token")
    if token:
        return token

    email = getattr(settings, "ESKIZ_EMAIL", "")
    password = getattr(settings, "ESKIZ_PASSWORD", "")

    try:
        auth_url = "https://notify.eskiz.uz/api/auth/login"
        response = requests.post(
            auth_url,
            data={
                "email": email,
                "password": password,
            },
            timeout=20,
        )

        data = response.json()

        if response.status_code == 200 and data.get("data", {}).get("token"):
            new_token = data["data"]["token"]
            cache.set("eskiz_auth_token", new_token, timeout=82800)  # 23 hours
            return new_token
        else:
            logger.error(f"Eskiz Login Failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Eskiz Auth Exception: {e}")
        return None


def send_eskiz_sms(phone: str, code: str):
    token = get_eskiz_token()
    if not token:
        logger.error("Eskiz token not available")
        return False

    from_name = getattr(settings, "ESKIZ_FROM", "4546")
    eskiz_phone = phone.replace("+", "")

    # Must match approved Eskiz template if your account requires it
    message = f"TaskiN: TaskiN platformasida ro’yxatdan o’tish uchun tasdiqlash kodingiz: {code}"

    try:
        send_url = "https://notify.eskiz.uz/api/message/sms/send"
        res = requests.post(
            send_url,
            headers={
                "Authorization": f"Bearer {token}",
            },
            data={
                "mobile_phone": eskiz_phone,
                "message": message,
                "from": from_name,
            },
            timeout=20,
        )

        if res.status_code == 200:
            logger.info(f"Eskiz SMS sent to {phone}")
            return True
        else:
            logger.error(f"Eskiz Send Failed: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        logger.error(f"Eskiz Send Exception: {e}")
        return False


def send_otp(phone: str) -> str:
    phone = normalize_phone(phone)

    # Google Play reviewer phones: no SMS, no cache write, nothing returned
    # that could leak (even via OTP_DEBUG_RETURN_CODE). verify_otp() checks
    # the fixed code from the environment instead of the cache.
    review_phones, _ = _play_review_config()
    if phone in review_phones:
        return ""

    # DEBUG-ONLY: fixed test numbers get a deterministic code and no SMS. Gated on
    # settings.DEBUG so it FAILS CLOSED in production — when DEBUG is False the dict
    # is ignored and the number falls through to the normal real-OTP path below.
    test_numbers = getattr(settings, "OTP_TEST_NUMBERS", {}) if settings.DEBUG else {}
    is_test_number = phone in test_numbers
    code = test_numbers[phone] if is_test_number else generate_otp_code()

    ttl = getattr(settings, "OTP_TTL_SECONDS", 120)
    # Store only the HASH of the code (never the plaintext). The plaintext `code`
    # is still returned for SMS delivery / the debug-return path. Test numbers use
    # the SAME storage path, so the same hashing/key/TTL applies and verify works
    # through the normal flow (lockout/expiry included).
    cache.set(otp_cache_key(phone), _hash_code(code), timeout=ttl)
    # NOTE: do NOT clear the failed-attempt counter here. The brute-force lockout
    # must persist independently of code issuance, otherwise a locked phone could
    # be reset simply by requesting a new code. The counter expires on its own
    # (~OTP_TTL_SECONDS) and is cleared on a successful verify.

    # Never attempt a real SMS for a fixed test number.
    if not is_test_number and getattr(settings, "ESKIZ_REAL_SMS", False):
        send_eskiz_sms(phone, code)

    return code


def verify_otp(phone: str, code: str) -> tuple[bool, str]:
    phone = normalize_phone(phone)
    code = (code or "").strip()

    # Google Play reviewer phones: constant-time check against the fixed code
    # from the environment. Only this branch for these numbers — the normal
    # HMAC/cache path below is untouched for every other number. Reviewers
    # share the SAME 5-attempt lockout counter mechanics (per phone), so the
    # fixed code cannot be brute-forced any faster than a real one; there is
    # no cached code to clear here, and the counter expires on its own
    # (~OTP_TTL), so a locked-out reviewer just waits it out.
    review_phones, review_code = _play_review_config()
    if phone in review_phones:
        attempts_key = otp_attempts_key(phone)

        if (cache.get(attempts_key) or 0) >= MAX_OTP_ATTEMPTS:
            return (False, "Too many attempts, request a new code.")

        if hmac.compare_digest(code.encode(), review_code.encode()):
            cache.delete(attempts_key)
            return (True, "")

        ttl = getattr(settings, "OTP_TTL_SECONDS", 120)
        cache.add(attempts_key, 0, ttl)
        attempts = cache.incr(attempts_key)
        if attempts >= MAX_OTP_ATTEMPTS:
            return (False, "Too many attempts, request a new code.")
        return (False, "Invalid or expired code")

    if getattr(settings, "FAKE_OTP_ENABLED", False):
        fake_code = str(getattr(settings, "FAKE_OTP_CODE", "111111")).strip()
        return (code == fake_code, "")

    # LOCAL DEV ONLY — never active in production (DEBUG=False on server)
    if settings.DEBUG and phone == "+998901112233":
        return (code == "999999", "")

    attempts_key = otp_attempts_key(phone)

    # Already locked out — reject until a new code is requested.
    if (cache.get(attempts_key) or 0) >= MAX_OTP_ATTEMPTS:
        cache.delete(otp_cache_key(phone))
        return (False, "Too many attempts, request a new code.")

    saved = cache.get(otp_cache_key(phone))
    if not saved:
        return (False, "Invalid or expired code")

    # Constant-time compare of the stored hash against the submitted code's hash.
    if secrets.compare_digest(str(saved), _hash_code(code)):
        # Success → clear both the code and the attempt counter.
        cache.delete(otp_cache_key(phone))
        cache.delete(attempts_key)
        return (True, "")

    # Wrong code → count this attempt atomically (avoids a get-then-set TOCTOU,
    # so parallel guesses can't overshoot the lock). `add` seeds the counter with
    # the OTP TTL only if absent; `incr` returns the post-increment value.
    ttl = getattr(settings, "OTP_TTL_SECONDS", 120)
    cache.add(attempts_key, 0, ttl)
    attempts = cache.incr(attempts_key)

    if attempts >= MAX_OTP_ATTEMPTS:
        cache.delete(otp_cache_key(phone))
        return (False, "Too many attempts, request a new code.")

    return (False, "Invalid or expired code")