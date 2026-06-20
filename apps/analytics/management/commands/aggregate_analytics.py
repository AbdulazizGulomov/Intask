# apps/analytics/management/commands/aggregate_analytics.py
"""
Nightly rollup of order data into the analytics summary tables.

Idempotent: re-running for the same dates produces the same rows (upsert via
update_or_create). Supports --since to limit the backfill window.

    python manage.py aggregate_analytics              # backfill all history
    python manage.py aggregate_analytics --since 2026-05-01
    python manage.py aggregate_analytics --days 7     # last 7 days only

Style mirrors apps/orders/management/commands/seed_dashboard.py.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Min
from django.utils import timezone

from apps.orders.models import Order, OrderStatusHistory
from apps.accounts.models import WorkerProfile
from apps.analytics.models import DailyMetric, DistrictProfessionDemand
from apps.analytics.utils import district_from_address, demand_status

ACCEPTED_STATUSES = {Order.Status.IN_PROGRESS, Order.Status.COMPLETED}


class Command(BaseCommand):
    help = "Roll up orders into analytics summary tables (DailyMetric, DistrictProfessionDemand)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="Recompute from this date forward (YYYY-MM-DD). Default: earliest order.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Only recompute the last N days (overrides --since).",
        )

    # ------------------------------------------------------------------ #
    def handle(self, *args, **options):
        today = timezone.localdate()

        start = self._resolve_start(options, today)
        if start is None:
            self.stdout.write(self.style.WARNING("No orders found — nothing to aggregate."))
            return

        self.stdout.write(
            self.style.SUCCESS(f"Aggregating analytics from {start} to {today} ...")
        )

        # --- Precompute lookups shared across all dates -------------------
        # Each employer's first-ever order date -> classifies new vs returning.
        first_order_date = {
            row["employer_id"]: timezone.localtime(row["first"]).date()
            for row in Order.objects.values("employer_id").annotate(first=Min("created_at"))
        }

        # Profession-level supply: active masters per profession.
        masters_by_profession = defaultdict(int)
        for wp in WorkerProfile.objects.filter(
            user__is_active=True, profession__isnull=False
        ).values("profession_id"):
            masters_by_profession[wp["profession_id"]] += 1

        # Worker -> (profession_id, profession_name)
        worker_profession = {}
        for wp in WorkerProfile.objects.filter(profession__isnull=False).select_related(
            "profession"
        ):
            worker_profession[wp.user_id] = (wp.profession_id, wp.profession.name)

        # First status-change timestamp per order (for time-to-assign).
        first_action = {
            row["order_id"]: row["first"]
            for row in OrderStatusHistory.objects.values("order_id").annotate(
                first=Min("created_at")
            )
        }

        # --- Pull the order cohort once ----------------------------------
        orders = (
            Order.objects.filter(created_at__date__gte=start, created_at__date__lte=today)
            .only(
                "id", "employer_id", "worker_id", "status", "agreed_price",
                "address", "created_at",
            )
        )

        daily = defaultdict(_blank_daily)            # (date, district) -> dict
        demand = defaultdict(lambda: defaultdict(int))  # (date, district) -> {prof_id: count}
        prof_names = {}
        seen_clients = defaultdict(lambda: {"new": set(), "ret": set()})

        for o in orders.iterator():
            d = timezone.localtime(o.created_at).date()
            district = district_from_address(o.address)
            key = (d, district)
            cell = daily[key]

            cell["orders_created"] += 1
            if o.worker_id:
                cell["orders_assigned"] += 1

            accepted = o.status in ACCEPTED_STATUSES or self._reached_accepted(o.id)
            completed = o.status == Order.Status.COMPLETED
            if accepted:
                cell["orders_accepted"] += 1
            if completed:
                cell["orders_completed"] += 1
                cell["gmv"] += o.agreed_price or Decimal("0")

            # time-to-assign: first status change minus creation
            fa = first_action.get(o.id)
            if fa:
                secs = int((fa - o.created_at).total_seconds())
                if secs >= 0:
                    cell["assign_time_sum_sec"] += secs
                    cell["assign_time_count"] += 1

            # new vs returning client
            if first_order_date.get(o.employer_id) == d:
                seen_clients[key]["new"].add(o.employer_id)
            else:
                seen_clients[key]["ret"].add(o.employer_id)

            # supply / demand by profession
            prof = worker_profession.get(o.worker_id)
            if prof:
                prof_id, prof_name = prof
                demand[key][prof_id] += 1
                prof_names[prof_id] = prof_name

        # Fold client sets into counts
        for key, buckets in seen_clients.items():
            daily[key]["new_clients"] = len(buckets["new"])
            daily[key]["returning_clients"] = len(buckets["ret"])

        # --- Upsert DailyMetric ------------------------------------------
        daily_written = 0
        for (d, district), vals in daily.items():
            DailyMetric.objects.update_or_create(
                date=d, district=district, defaults=vals
            )
            daily_written += 1

        # --- Upsert DistrictProfessionDemand -----------------------------
        demand_written = 0
        for (d, district), prof_counts in demand.items():
            for prof_id, count in prof_counts.items():
                supply = masters_by_profession.get(prof_id, 0)
                DistrictProfessionDemand.objects.update_or_create(
                    date=d,
                    district=district,
                    profession_id=prof_id,
                    defaults={
                        "demand_count": count,
                        "available_masters": supply,
                        "status": demand_status(count, supply),
                    },
                )
                demand_written += 1

        self.stdout.write(self.style.SUCCESS("=" * 56))
        self.stdout.write(self.style.SUCCESS("  Aggregation complete"))
        self.stdout.write(self.style.SUCCESS(f"  DailyMetric rows upserted:               {daily_written}"))
        self.stdout.write(self.style.SUCCESS(f"  DistrictProfessionDemand rows upserted:  {demand_written}"))
        self.stdout.write(self.style.SUCCESS("=" * 56))

    # ------------------------------------------------------------------ #
    def _resolve_start(self, options, today):
        if options.get("days"):
            return today - timedelta(days=options["days"] - 1)
        if options.get("since"):
            try:
                return datetime.strptime(options["since"], "%Y-%m-%d").date()
            except ValueError:
                self.stderr.write(self.style.ERROR("Invalid --since date; use YYYY-MM-DD."))
                raise SystemExit(1)
        first = Order.objects.order_by("created_at").values_list("created_at", flat=True).first()
        if first is None:
            return None
        return timezone.localtime(first).date()

    def _reached_accepted(self, order_id):
        return OrderStatusHistory.objects.filter(
            order_id=order_id, to_status__in=ACCEPTED_STATUSES
        ).exists()


def _blank_daily():
    return {
        "gmv": Decimal("0"),
        "orders_created": 0,
        "orders_assigned": 0,
        "orders_accepted": 0,
        "orders_completed": 0,
        "assign_time_sum_sec": 0,
        "assign_time_count": 0,
        "new_clients": 0,
        "returning_clients": 0,
    }