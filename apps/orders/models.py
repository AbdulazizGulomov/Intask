# apps/orders/models.py
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Order(models.Model):
    """
    Real work contract between an employer and a worker.
    Created when a JobApplication is accepted.
    """

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Scheduled")
        IN_PROGRESS = "in_progress", _("In Progress")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")
        DISPUTED = "disputed", _("Disputed")

    # Source link (optional — orders can be created from a job application or directly)
    job_application = models.OneToOneField(
        "jobs.JobApplication",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order",
        verbose_name=_("Job application"),
    )

    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("Job"),
    )

    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders_as_employer",
        verbose_name=_("Employer"),
    )

    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders_as_worker",
        verbose_name=_("Worker"),
    )

    # Snapshot of the deal (so it survives even if Job is edited/deleted)
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    description = models.TextField(blank=True, default="", verbose_name=_("Description"))

    # Money
    agreed_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Agreed price"),
    )
    currency = models.CharField(
        max_length=3,
        default="UZS",
        verbose_name=_("Currency"),
    )

    # Schedule
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Scheduled at"),
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Started at"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Completed at"))

    # Location
    address = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Address"),
    )
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        verbose_name=_("Status"),
    )

    # Rating (filled after completion)
    employer_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=_("Employer rates the worker (1-5)"),
        verbose_name=_("Worker rating"),
    )
    worker_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=_("Worker rates the employer (1-5)"),
        verbose_name=_("Employer rating"),
    )
    employer_review = models.TextField(blank=True, default="")
    worker_review = models.TextField(blank=True, default="")

    # Cancellation
    cancellation_reason = models.TextField(blank=True, default="")
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_orders",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return f"Order #{self.pk} — {self.title}"


class OrderStatusHistory(models.Model):
    """Audit log: every status change of an order."""

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name=_("Order"),
    )

    from_status = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name=_("From status"),
    )
    to_status = models.CharField(
        max_length=20,
        verbose_name=_("To status"),
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_changes",
        verbose_name=_("Changed by"),
    )

    note = models.TextField(blank=True, default="", verbose_name=_("Note"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Status change")
        verbose_name_plural = _("Status history")

    def __str__(self):
        return f"#{self.order_id}: {self.from_status} → {self.to_status}"