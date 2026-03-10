import requests
from django.conf import settings

LOGIN_URL = "https://notify.eskiz.uz/api/auth/login"
SEND_SMS_URL = "https://notify.eskiz.uz/api/message/sms/send"


def get_eskiz_token():
    response = requests.post(
        LOGIN_URL,
        data={
            "email": settings.ESKIZ_EMAIL,
            "password": settings.ESKIZ_PASSWORD,
        },
        timeout=15,
    )

    response.raise_for_status()
    data = response.json()

    token = data.get("data", {}).get("token")
    if not token:
        raise Exception(f"Eskiz token not found. Response: {data}")

    return token


def send_sms(phone: str, message: str):
    token = get_eskiz_token()

    response = requests.post(
        SEND_SMS_URL,
        headers={
            "Authorization": f"Bearer {token}",
        },
        data={
            "mobile_phone": phone,
            "message": message,
            "from": settings.ESKIZ_FROM,
        },
        timeout=15,
    )

    response.raise_for_status()
    return response.json()


def send_otp_sms(phone: str, otp_code: str):
    message = f"Intask platformasida ro'yxatdan o'tish uchun tasdiqlash kodingiz: {otp_code}. Kod 2 daqiqa ichida amal qiladi."
    return send_sms(phone, message)