from django.db import models
from django.utils.translation import gettext_lazy as _


class Profession(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = _("Profession")
        verbose_name_plural = _("Professions")

    def __str__(self):
        return self.name


class Job(models.Model):
    class JobType(models.TextChoices):
        DOIMIY = "doimiy", _("Doimiy")
        VAQTINCHALIK = "vaqtinchalik", _("Vaqtinchalik")

    class Currency(models.TextChoices):
        UZS = "UZS", _("UZS")
        USD = "USD", _("USD")

    employer = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="jobs",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=255)

    region = models.CharField(
        max_length=50,
        help_text=_("Region key, e.g. buxoro, toshkent_city"),
    )

    job_type = models.CharField(
        max_length=20,
        choices=JobType.choices,
    )

    profession = models.ForeignKey(
        "jobs.Profession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
        verbose_name=_("Profession"),
    )

    pay_currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.UZS,
    )

    pay_min = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    pay_max = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    pay_text = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text=_("Old salary text (optional), e.g. '6–8 mln so‘m'"),
    )

    photo1 = models.ImageField(upload_to="job_photos/", null=True, blank=True)
    photo2 = models.ImageField(upload_to="job_photos/", null=True, blank=True)
    photo3 = models.ImageField(upload_to="job_photos/", null=True, blank=True)
    photo4 = models.ImageField(upload_to="job_photos/", null=True, blank=True)

    description = models.TextField(blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")

    lat = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Latitude for map pin"),
    )

    lng = models.FloatField(
        null=True,
        blank=True,
        help_text=_("Longitude for map pin"),
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Job")
        verbose_name_plural = _("Jobs")

    def __str__(self):
        return f"{self.title} ({self.region})"


class JobApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACCEPTED = "accepted", _("Accepted")
        REJECTED = "rejected", _("Rejected")

    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="applications",
    )
    worker = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="job_applications",
    )
    employer = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="received_job_applications",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("job", "worker")
        ordering = ["-created_at"]
        verbose_name = _("Job Application")
        verbose_name_plural = _("Job Applications")

    def __str__(self):
        return f"{self.worker} -> {self.job.title}"