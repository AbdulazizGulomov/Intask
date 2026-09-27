# apps/moderation/serializers.py
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.jobs.models import Job
from apps.moderation.filters import validate_clean_text
from apps.moderation.models import Block, Report

User = get_user_model()


class ReportCreateSerializer(serializers.ModelSerializer):
    """POST /api/reports/ — the reporter comes from the request, never the body."""

    target_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    target_job = serializers.PrimaryKeyRelatedField(
        queryset=Job.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Report
        fields = ["id", "target_type", "target_user", "target_job", "reason", "comment", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def validate_comment(self, value):
        # A report is still user-generated text that operators read.
        validate_clean_text(value, "comment")
        return value

    def validate(self, attrs):
        target_type = attrs.get("target_type")
        target_user = attrs.get("target_user")
        target_job = attrs.get("target_job")
        reporter = self.context["request"].user

        if target_type == Report.TargetType.USER:
            if not target_user:
                raise serializers.ValidationError(
                    {"target_user": [_("target_user is required when target_type is 'user'.")]}
                )
            if target_job:
                raise serializers.ValidationError(
                    {"target_job": [_("target_job must be empty when target_type is 'user'.")]}
                )
            if target_user.pk == reporter.pk:
                raise serializers.ValidationError(
                    {"target_user": [_("You cannot report yourself.")]}
                )
        elif target_type == Report.TargetType.JOB:
            if not target_job:
                raise serializers.ValidationError(
                    {"target_job": [_("target_job is required when target_type is 'job'.")]}
                )
            if target_user:
                raise serializers.ValidationError(
                    {"target_user": [_("target_user must be empty when target_type is 'job'.")]}
                )
            if target_job.employer_id == reporter.pk:
                raise serializers.ValidationError(
                    {"target_job": [_("You cannot report your own job.")]}
                )

        attrs["reporter"] = reporter
        return attrs


class ReportSerializer(serializers.ModelSerializer):
    """What POST /api/reports/ returns to the app."""

    class Meta:
        model = Report
        fields = [
            "id", "target_type", "target_user", "target_job",
            "reason", "comment", "status", "created_at",
        ]
        read_only_fields = fields


class BlockedUserSerializer(serializers.Serializer):
    """The blocked party, as GET /api/blocks/ lists them."""

    id = serializers.IntegerField(source="blocked_id", read_only=True)
    phone = serializers.CharField(source="blocked.phone", read_only=True, allow_null=True)
    full_name = serializers.SerializerMethodField()
    blocked_at = serializers.DateTimeField(source="created_at", read_only=True)

    def get_full_name(self, obj) -> str:
        wp = getattr(obj.blocked, "worker_profile", None)
        if wp is None:
            return ""
        return (wp.full_name or f"{wp.first_name} {wp.last_name}".strip() or "")
