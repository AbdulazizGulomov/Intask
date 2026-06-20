# apps/analytics/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _


class DailyMetric(models.Model):
    """
    Pre-aggregated per-day, per-district analytics rollup.

    All counters are COHORT metrics for orders *created* on `date` in
    `district` (so funnel + fill_rate stay internally consistent). Rates are
    NOT stored — only their additive components — so a date-range query can sum
    rows and compute the rate correctly.

    Rolled up nightly by `manage.py aggregate_analytics` (idempotent upsert).
    """

    date = models.DateField(verbose_name=_("Date"))
    district = models.CharField(max_length=100, verbose_name=_("District"))

    # Money — GMV of orders created this day (in this district) that completed
    gmv = models.DecimalField(
        max_digits=16, decimal_places=2, default=0, verbose_name=_("GMV")
    )

    # Funnel counters (cohort by created date)
    orders_created = models.PositiveIntegerField(default=0)
    orders_assigned = models.PositiveIntegerField(default=0)
    orders_accepted = models.PositiveIntegerField(default=0)
    orders_completed = models.PositiveIntegerField(default=0)

    # Time-to-assign — store sum + count so range averages are correct
    assign_time_sum_sec = models.BigIntegerField(default=0)
    assign_time_count = models.PositiveIntegerField(default=0)

    # Clients active this day (by their first-ever order date)
    new_clients = models.PositiveIntegerField(default=0)
    returning_clients = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Daily metric")
        verbose_name_plural = _("Daily metrics")
        ordering = ["-date", "district"]
        constraints = [
            models.UniqueConstraint(
                fields=["date", "district"], name="uniq_dailymetric_date_district"
            )
        ]
        indexes = [models.Index(fields=["date"])]

    def __str__(self):
        return f"{self.date} · {self.district}"


class DistrictProfessionDemand(models.Model):
    """
    Per-day supply/demand snapshot for a (district, profession) pair.

    demand_count     = orders created that day in `district` whose worker has
                       this profession.
    available_masters = number of active masters with this profession
                       (profession-level supply; workers have no district in
                       this schema, so supply is not district-segmented).
    status           = ok / tight / gap derived from demand vs supply.
    """

    class Status(models.TextChoices):
        OK = "ok", _("OK")
        TIGHT = "tight", _("Tight")
        GAP = "gap", _("Gap")

    date = models.DateField(verbose_name=_("Date"))
    district = models.CharField(max_length=100, verbose_name=_("District"))
    profession = models.ForeignKey(
        "jobs.Profession",
        on_delete=models.CASCADE,
        related_name="demand_snapshots",
        verbose_name=_("Profession"),
    )

    demand_count = models.PositiveIntegerField(default=0)
    available_masters = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OK
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("District/profession demand")
        verbose_name_plural = _("District/profession demand")
        ordering = ["-date", "district", "profession"]
        constraints = [
            models.UniqueConstraint(
                fields=["date", "district", "profession"],
                name="uniq_demand_date_district_profession",
            )
        ]
        indexes = [models.Index(fields=["date"])]

    def __str__(self):
        return f"{self.date} · {self.district} · {self.profession_id}"