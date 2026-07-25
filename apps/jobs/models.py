# apps/jobs/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _


class Job(models.Model):
    class JobType(models.TextChoices):
        HOURLY = "hourly", _("Hourly")
        DAILY = "daily", _("Daily")

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

    profession = models.ForeignKey(
        "jobs.Profession",
        on_delete=models.SET_NULL,
        related_name="jobs",
        null=True,
        blank=True,
        verbose_name=_("Profession"),
    )

    region = models.CharField(
        max_length=50,
        help_text=_("Region key, e.g. buxoro, toshkent_city"),
    )

    job_type = models.CharField(max_length=20, choices=JobType.choices)

    # structured pay
    pay_currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.UZS,
    )
    pay_min = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    pay_max = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    # optional text pay
    pay_text = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text=_("Old salary text (optional), e.g. '6–8 mln so‘m'"),
    )

    #  NEW: 4 photos
    photo1 = models.ImageField(upload_to="job_photos/", null=True, blank=True)
    photo2 = models.ImageField(upload_to="job_photos/", null=True, blank=True)
    photo3 = models.ImageField(upload_to="job_photos/", null=True, blank=True)
    photo4 = models.ImageField(upload_to="job_photos/", null=True, blank=True)

    description = models.TextField(blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")

    lat = models.FloatField(null=True, blank=True, help_text=_("Latitude for map pin"))
    lng = models.FloatField(null=True, blank=True, help_text=_("Longitude for map pin"))
    address = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Human-readable address from the map picker (reverse-geocoded or typed)"),
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


class Profession(models.Model):
    name = models.CharField(max_length=100, unique=True)  # Uzbek default
    name_ru = models.CharField(max_length=128, blank=True, default="")
    name_en = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        verbose_name = _("Profession")
        verbose_name_plural = _("Professions")

    def display_name(self, lang):
        """Localized name for the active language, falling back to Uzbek."""
        return (
            self.name_ru if (lang == "ru" and self.name_ru)
            else self.name_en if (lang == "en" and self.name_en)
            else self.name
        )

    def __str__(self):
        return self.name


class JobApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

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
        verbose_name = "Job Application"
        verbose_name_plural = "Job Applications"
        ordering = ["-created_at"]
        unique_together = (("job", "worker"),)

    def __str__(self):
        return f"Application #{self.pk} (job={self.job_id}, worker={self.worker_id})"
