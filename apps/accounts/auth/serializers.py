import re

from rest_framework import serializers

from .otp import normalize_phone

# A normalized UZ mobile number: +998 followed by exactly 9 digits.
UZ_PHONE_RE = re.compile(r"^\+998\d{9}$")


def is_valid_uz_phone(value: str) -> bool:
    """True if `value` normalizes to a valid +998XXXXXXXXX number."""
    return bool(UZ_PHONE_RE.match(normalize_phone(value)))


class SendOtpSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        normalized = normalize_phone(value)
        if not UZ_PHONE_RE.match(normalized):
            # Generic, non-enumerating message.
            raise serializers.ValidationError("Enter a valid phone number.")
        return normalized


class VerifyOtpSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)
