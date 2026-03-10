from rest_framework import serializers

class SendOtpSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

class VerifyOtpSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)
