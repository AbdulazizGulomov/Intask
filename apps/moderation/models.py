# apps/moderation/models.py
"""User-generated-content safety models (App Store Guideline 1.2).

Report  — a user flags another user or a job listing for operator review.
Block   — a user hides another user from their side of the app, in both
          directions (see apps.moderation.selectors.blocked_user_ids).
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Report(models.Model):
    """One abuse report, awaiting operator action.

    Operators are committed to acting within 24h of `created_at` — the
    dashboard surfaces `hours_open` / `is_overdue` off this timestamp.
    """

    class TargetType(models.TextChoices):
        USER = "user", _("User")
        JOB = "job", _("Job")

    class Reason(models.TextChoices):
        SPAM = "spam", _("Spam")
        ABUSE = "abuse", _("Abuse or harassment")
        FRAUD = "fraud", _("Fraud or scam")
        INAPPROPRIATE = "inappropriate", _("Inappropriate content")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        RESOLVED = "resolved", _("Resolved")
        REJECTED = "rejected", _("Rejected")

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_filed",
        verbose_name=_("Reporter"),
    )

    target_type = models.CharField(max_length=10, choices=TargetType.choices)

    # Exactly one of these is set, matching target_type — enforced by clean()
    # and by the API serializer.
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports_received",
        verbose_name=_("Reported user"),
    )
    target_job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports",
        verbose_name=_("Reported job"),
    )

    reason = models.CharField(max_length=20, choices=Reason.choices)
    comment = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_resolved",
        verbose_name=_("Resolved by"),
    )

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ["-created_at"]
        constraints = [
            # "One OPEN report per reporter+target" — partial uniqueness, so a
            # closed report never blocks a legitimate re-report of a repeat
            # offender. unique_together could not express the status condition.
            models.UniqueConstraint(
                fields=["reporter", "target_user"],
                condition=models.Q(status="open"),
                name="uniq_open_report_per_reporter_user",
            ),
            models.UniqueConstraint(
                fields=["reporter", "target_job"],
                condition=models.Q(status="open"),
                name="uniq_open_report_per_reporter_job",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        target = self.target_user_id if self.target_type == self.TargetType.USER else self.target_job_id
        return f"Report #{self.pk} ({self.target_type}={target}, {self.reason})"

    @property
    def is_open(self) -> bool:
        return self.status == self.Status.OPEN


class Block(models.Model):
    """`blocker` no longer wants to see `blocked` anywhere in the app.

    Enforcement is symmetric — see selectors.blocked_user_ids — so a block
    hides each party from the other regardless of who created the row.
    """

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_made",
        verbose_name=_("Blocker"),
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocks_received",
        verbose_name=_("Blocked user"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Block")
        verbose_name_plural = _("Blocks")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"], name="uniq_block_pair"
            ),
        ]

    def __str__(self):
        return f"Block({self.blocker_id} -> {self.blocked_id})"
