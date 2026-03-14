# apps/accounts/auth/otp.py
import logging
import random
import re

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """
    Normalize Uzbek phone to: +998901234567

    Accepts:
    901234567
    998901234567
    +998901234567
    +998 90 123 45 67
    """
    p = (phone or "").strip()
    digits = re.sub(r"\D", "", p)

    # local 9-digit number -> prepend country code
    if len(digits) == 9:
        digits = "998" + digits

    # already correct Uzbekistan format
    if len(digits) == 12 and digits.startswith("998"):
        return "+" + digits

    # invalid format
    return ""


def generate_otp_code() -> str:
    return f"{random.randint(100000, 999999)}"


def otp_cache_key(phone: str) -> str:
    return f"otp:{phone}"


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
    eskiz_phone = re.sub(r"\D", "", phone)  # final Eskiz format: 998901234567

    print("===== ESKIZ SMS DEBUG =====")
    print("phone =", phone)
    print("eskiz_phone =", eskiz_phone)
    print("from_name =", from_name)
    print("code =", code)
    print("===========================")

    if len(eskiz_phone) != 12 or not eskiz_phone.startswith("998"):
        logger.error(f"Eskiz Send Blocked: invalid normalized phone -> {eskiz_phone}")
        return False

    message = f"Intask platformasida ro'yxatdan o'tish uchun tasdiqlash kodingiz: {code}. Kod 2 daqiqa ichida amal qiladi."

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

        print("===== ESKIZ RESPONSE DEBUG =====")
        print("status_code =", res.status_code)
        print("response_text =", res.text)
        print("================================")

        if res.status_code == 200:
            logger.info(f"Eskiz SMS sent to {phone}")
            return True

        logger.error(f"Eskiz Send Failed: {res.status_code} - {res.text}")
        return False

    except Exception as e:
        logger.error(f"Eskiz Send Exception: {e}")
        return False


def send_otp(phone: str) -> str:
    original_phone = phone
    phone = normalize_phone(phone)
    code = generate_otp_code()

    print("===== SEND OTP DEBUG =====")
    print("original_phone =", original_phone)
    print("normalized_phone =", phone)
    print("eskiz_phone =", re.sub(r'\\D', '', phone))
    print("generated_code =", code)
    print("==========================")

    if not phone:
        logger.error(f"OTP send blocked: invalid phone input -> {original_phone}")
        return code

    ttl = getattr(settings, "OTP_TTL_SECONDS", 120)
    cache.set(otp_cache_key(phone), code, timeout=ttl)

    if getattr(settings, "ESKIZ_REAL_SMS", False):
        send_eskiz_sms(phone, code)

    return code


def verify_otp(phone: str, code: str) -> bool:
    phone = normalize_phone(phone)
    code = (code or "").strip()

    print("===== VERIFY OTP CORE DEBUG =====")
    print("normalized_phone =", phone)
    print("input_code =", code)
    print("cache_key =", otp_cache_key(phone))
    print("saved_code =", cache.get(otp_cache_key(phone)))
    print("=================================")

    if getattr(settings, "FAKE_OTP_ENABLED", False):
        fake_code = str(getattr(settings, "FAKE_OTP_CODE", "111111")).strip()
        return code == fake_code

    if not phone:
        return False

    saved = cache.get(otp_cache_key(phone))
    if not saved:
        return False

    ok = str(saved).strip() == code
    if ok:
        cache.delete(otp_cache_key(phone))
    return ok