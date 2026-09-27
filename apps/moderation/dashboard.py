# apps/moderation/dashboard.py
"""Operator-facing moderation queue (App Store Guideline 1.2).

Apple requires acting on abuse reports within 24 hours, so the queue is
ordered oldest-open-first and every row carries how long it has been waiting.

  GET  /api/dashboard/reports/                       the queue
  GET  /api/dashboard/reports/<id>/                  one report
  POST /api/dashboard/reports/<id>/resolve/          action taken
  POST /api/dashboard/reports/<id>/reject/           no violation found
  POST /api/dashboard/reports/<id>/hide-job/         deactivate the job, resolve
  POST /api/dashboard/reports/<id>/deactivate-user/  deactivate the user, resolve
"""

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import filters, mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.dashboard.permissions import IsOperatorOrAdmin
from apps.accounts.models import User
from apps.moderation.models import Report


def _sla_hours() -> int:
    return int(getattr(settings, "MODERATION_SLA_HOURS", 24))


class ReportUserSerializer(serializers.ModelSerializer):
    """Slim user shape reused for reporter / target / resolver."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "phone", "role", "is_active", "full_name")

    def get_full_name(self, obj) -> str:
        wp = getattr(obj, "worker_profile", None)
        if wp is None:
            return ""
        return wp.full_name or f"{wp.first_name} {wp.last_name}".strip() or ""


class ReportSerializer(serializers.ModelSerializer):
    """One row of the moderation queue."""

    reporter = ReportUserSerializer(read_only=True)
    target_user = ReportUserSerializer(read_only=True)
    target_job = serializers.SerializerMethodField()
    resolved_by = ReportUserSerializer(read_only=True)
    hours_open = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    sla_hours = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            "id", "reporter", "target_type", "target_user", "target_job",
            "reason", "comment", "status",
            "created_at", "resolved_at", "resolved_by",
            "hours_open", "is_overdue", "sla_hours",
        )
        read_only_fields = fields

    def get_target_job(self, obj):
        job = obj.target_job
        if job is None:
            return None
        return {
            "id": job.id,
            "title": job.title,
            "is_active": job.is_active,
            "employer_id": job.employer_id,
        }

    def get_hours_open(self, obj) -> float:
        """How long the report has been waiting, or how long it took to close.

        Open reports measure to now, so the number keeps climbing and the row
        stays visibly overdue. Closed ones freeze at resolved_at, which is the
        turnaround time that actually matters afterwards.
        """
        end = timezone.now() if obj.is_open else (obj.resolved_at or timezone.now())
        return round((end - obj.created_at).total_seconds() / 3600.0, 1)

    def get_is_overdue(self, obj) -> bool:
        """Only OPEN reports can be overdue - a closed one was handled."""
        return bool(obj.is_open and self.get_hours_open(obj) > _sla_hours())

    def get_sla_hours(self, obj) -> int:
        return _sla_hours()


class ReportsPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class ReportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only queue plus the four moderation actions. Operators/admins only.

    Deliberately not block-filtered: operators must see every report,
    including ones between users who have blocked each other.
    """

    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]
    pagination_class = ReportsPagination
    serializer_class = ReportSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["comment", "reporter__phone", "target_user__phone", "target_job__title"]
    ordering_fields = ["created_at", "resolved_at", "status"]

    def get_queryset(self):
        qs = Report.objects.select_related(
            "reporter", "reporter__worker_profile",
            "target_user", "target_user__worker_profile",
            "target_job",
            "resolved_by", "resolved_by__worker_profile",
        )

        status_param = self.request.query_params.get("status")
        if status_param:
            wanted = [s.strip() for s in status_param.split(",") if s.strip()]
            qs = qs.filter(status__in=wanted)

        # Open first, then oldest first - so the report closest to breaching
        # the 24h commitment sits at the top of the queue.
        return qs.annotate(
            sort_group=models.Case(
                models.When(status=Report.Status.OPEN, then=0),
                default=1,
                output_field=models.IntegerField(),
            )
        ).order_by("sort_group", "created_at")

    # ---- actions --------------------------------------------------------

    def _close(self, report, new_status, request):
        report.status = new_status
        report.resolved_at = timezone.now()
        report.resolved_by = request.user
        report.save(update_fields=["status", "resolved_at", "resolved_by"])
        return report

    def _respond(self, report):
        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        report = self.get_object()
        self._close(report, Report.Status.RESOLVED, request)
        return self._respond(report)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        report = self.get_object()
        self._close(report, Report.Status.REJECTED, request)
        return self._respond(report)

    @action(detail=True, methods=["post"], url_path="hide-job")
    def hide_job(self, request, pk=None):
        """Deactivate the reported job and resolve the report in one step."""
        report = self.get_object()
        job = report.target_job
        if job is None:
            return Response(
                {"detail": _("This report does not target a job.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            if job.is_active:
                job.is_active = False
                job.save(update_fields=["is_active"])
            self._close(report, Report.Status.RESOLVED, request)
        report.refresh_from_db()
        return self._respond(report)

    @action(detail=True, methods=["post"], url_path="deactivate-user")
    def deactivate_user(self, request, pk=None):
        """Deactivate the reported user and resolve the report in one step.

        For a job report this targets the job's employer, so an operator can
        act on a listing's author without hunting down a second report.
        """
        report = self.get_object()
        target = report.target_user or (
            report.target_job.employer if report.target_job else None
        )
        if target is None:
            return Response(
                {"detail": _("This report has no user to deactivate.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Staff and operators are out of reach of this button - removing one of
        # those is an admin action, not a moderation one.
        if (
            target.is_staff
            or target.is_superuser
            or target.role in (User.Role.OPERATOR, User.Role.ADMIN)
        ):
            return Response(
                {"detail": _("Staff and operator accounts cannot be deactivated here.")},
                status=status.HTTP_403_FORBIDDEN,
            )
        with transaction.atomic():
            if target.is_active:
                target.is_active = False
                target.save(update_fields=["is_active"])
            self._close(report, Report.Status.RESOLVED, request)
        report.refresh_from_db()
        return self._respond(report)
