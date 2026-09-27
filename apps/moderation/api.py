# apps/moderation/api.py
"""Mobile-facing UGC safety endpoints (App Store Guideline 1.2).

  POST   /api/reports/            file an abuse report
  GET    /api/blocks/             list who I have blocked
  POST   /api/blocks/             block a user
  DELETE /api/blocks/<user_id>/   unblock a user
"""

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.moderation.models import Block, Report
from apps.moderation.serializers import (
    BlockedUserSerializer,
    ReportCreateSerializer,
    ReportSerializer,
)

User = get_user_model()


class ReportCreateAPIView(APIView):
    """POST /api/reports/ — file a report against a user or a job.

    409 when this reporter already has an OPEN report for the same target;
    filing again once the first is closed is allowed (repeat offenders).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        validated = dict(serializer.validated_data)
        target_user = validated.get("target_user")
        target_job = validated.get("target_job")

        # Check before insert so the common case gets a clean 409 rather than a
        # constraint error; the DB constraint is still the source of truth for
        # concurrent duplicates, caught below.
        duplicate = Report.objects.filter(
            reporter=request.user,
            status=Report.Status.OPEN,
            target_user=target_user,
            target_job=target_job,
        ).exists()
        if duplicate:
            return Response(
                {"detail": _("You already have an open report for this target.")},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            report = Report.objects.create(**validated)
        except IntegrityError:
            return Response(
                {"detail": _("You already have an open report for this target.")},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


class BlockListCreateAPIView(APIView):
    """GET /api/blocks/ — users I have blocked (my own blocks only).
    POST /api/blocks/ — block a user by id. Idempotent: re-blocking returns 200.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        blocks = (
            Block.objects.filter(blocker=request.user)
            .select_related("blocked", "blocked__worker_profile")
            .order_by("-created_at")
        )
        return Response(BlockedUserSerializer(blocks, many=True).data)

    def post(self, request):
        raw_id = request.data.get("user_id", request.data.get("blocked"))
        if raw_id in (None, ""):
            return Response(
                {"user_id": [_("This field is required.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            target_id = int(raw_id)
        except (TypeError, ValueError):
            return Response(
                {"user_id": [_("Must be a numeric user id.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if target_id == request.user.id:
            return Response(
                {"user_id": [_("You cannot block yourself.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target = get_object_or_404(User, pk=target_id)

        _block, created = Block.objects.get_or_create(blocker=request.user, blocked=target)
        return Response(
            {"blocked": target.id, "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class BlockDeleteAPIView(APIView):
    """DELETE /api/blocks/<user_id>/ — unblock. 204 whether or not a row existed."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id):
        Block.objects.filter(blocker=request.user, blocked_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
