# apps/analytics/api_views.py
"""
Operator-gated analytics endpoints. Mounted under /api/dashboard/analytics/.

All read from the pre-aggregated summary tables (DailyMetric,
DistrictProfessionDemand) — no heavy per-request order scans. Every endpoint
accepts ?from=&to=&district= and returns zeros/empty (never 500) for empty
ranges. Rounding is done here, matching the dashboard views' style.
"""
from collections import defaultdict, OrderedDict

from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.dashboard.permissions import IsOperatorOrAdmin
from apps.orders.models import Order
from apps.jobs.models import JobApplication
from .models import DailyMetric, DistrictProfessionDemand
from .utils import resolve_range, previous_range, pct_delta, demand_status


class _AnalyticsBase(APIView):
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]

    def _daily_qs(self, date_from, date_to, district):
        qs = DailyMetric.objects.filter(date__gte=date_from, date__lte=date_to)
        if district:
            qs = qs.filter(district__iexact=district)
        return qs


class AnalyticsKpisView(_AnalyticsBase):
    """GET /kpis/ -> gmv, fill_rate, avg_time_to_assign, repeat_client_rate (+ deltas)."""

    def get(self, request):
        date_from, date_to = resolve_range(request)
        prev_from, prev_to = previous_range(date_from, date_to)
        district = request.query_params.get("district") or ""

        cur = self._totals(self._daily_qs(date_from, date_to, district))
        prev = self._totals(self._daily_qs(prev_from, prev_to, district))

        return Response({
            "range": {"from": str(date_from), "to": str(date_to)},
            "kpis": {
                "gmv": self._kpi(cur["gmv"], prev["gmv"]),
                "fill_rate": self._kpi(cur["fill_rate"], prev["fill_rate"]),
                "avg_time_to_assign": self._kpi(
                    cur["avg_assign_sec"], prev["avg_assign_sec"]
                ),
                "repeat_client_rate": self._kpi(
                    cur["repeat_rate"], prev["repeat_rate"]
                ),
            },
        })

    def _totals(self, qs):
        agg = qs.aggregate(
            gmv=Sum("gmv"),
            created=Sum("orders_created"),
            completed=Sum("orders_completed"),
            assign_sum=Sum("assign_time_sum_sec"),
            assign_cnt=Sum("assign_time_count"),
            new_c=Sum("new_clients"),
            ret_c=Sum("returning_clients"),
        )
        created = agg["created"] or 0
        completed = agg["completed"] or 0
        assign_sum = agg["assign_sum"] or 0
        assign_cnt = agg["assign_cnt"] or 0
        new_c = agg["new_c"] or 0
        ret_c = agg["ret_c"] or 0
        return {
            "gmv": round(float(agg["gmv"] or 0), 2),
            "fill_rate": round(completed / created * 100, 1) if created else 0.0,
            "avg_assign_sec": round(assign_sum / assign_cnt, 1) if assign_cnt else 0.0,
            "repeat_rate": round(ret_c / (new_c + ret_c) * 100, 1) if (new_c + ret_c) else 0.0,
        }

    @staticmethod
    def _kpi(value, prev_value):
        return {"value": value, "prev": prev_value, "delta_pct": pct_delta(value, prev_value)}


class AnalyticsFunnelView(_AnalyticsBase):
    """GET /funnel/ -> primary lifecycle funnel + secondary application funnel."""

    def get(self, request):
        date_from, date_to = resolve_range(request)
        district = request.query_params.get("district") or ""

        agg = self._daily_qs(date_from, date_to, district).aggregate(
            created=Sum("orders_created"),
            assigned=Sum("orders_assigned"),
            accepted=Sum("orders_accepted"),
            completed=Sum("orders_completed"),
        )
        created = agg["created"] or 0
        stages = [
            ("created", created),
            ("assigned", agg["assigned"] or 0),
            ("accepted", agg["accepted"] or 0),
            ("completed", agg["completed"] or 0),
        ]
        primary = []
        prev_count = None
        for label, count in stages:
            primary.append({
                "stage": label,
                "count": count,
                "pct_of_created": round(count / created * 100, 1) if created else 0.0,
                "dropoff_pct": (
                    round((prev_count - count) / prev_count * 100, 1)
                    if prev_count else 0.0
                ),
            })
            prev_count = count

        return Response({
            "range": {"from": str(date_from), "to": str(date_to)},
            "primary": primary,
            "secondary": self._application_funnel(date_from, date_to),
        })

    def _application_funnel(self, date_from, date_to):
        """Workers applying to jobs: applied -> accepted -> completed (linked order)."""
        qs = JobApplication.objects.filter(
            created_at__date__gte=date_from, created_at__date__lte=date_to
        )
        applied = qs.count()
        accepted = qs.filter(status="accepted").count()
        completed = Order.objects.filter(
            job_application__in=qs, status=Order.Status.COMPLETED
        ).count()
        stages = [("applied", applied), ("accepted", accepted), ("completed", completed)]
        out = []
        for label, count in stages:
            out.append({
                "stage": label,
                "count": count,
                "pct_of_applied": round(count / applied * 100, 1) if applied else 0.0,
            })
        return out


class AnalyticsClientsTrendView(_AnalyticsBase):
    """GET /clients-trend/ -> weekly new vs returning clients."""

    def get(self, request):
        date_from, date_to = resolve_range(request)
        district = request.query_params.get("district") or ""

        rows = self._daily_qs(date_from, date_to, district).values(
            "date", "new_clients", "returning_clients"
        ).order_by("date")

        weeks = OrderedDict()
        for r in rows:
            iso = r["date"].isocalendar()
            key = (iso[0], iso[1])
            if key not in weeks:
                # Monday of that ISO week as the label
                monday = r["date"].fromisocalendar(iso[0], iso[1], 1)
                weeks[key] = {"week": str(monday), "new": 0, "returning": 0}
            weeks[key]["new"] += r["new_clients"]
            weeks[key]["returning"] += r["returning_clients"]

        return Response({
            "range": {"from": str(date_from), "to": str(date_to)},
            "weeks": list(weeks.values()),
        })


class AnalyticsSupplyDemandView(_AnalyticsBase):
    """GET /supply-demand/ -> district x profession matrix with ok/tight/gap status."""

    def get(self, request):
        date_from, date_to = resolve_range(request)
        district = request.query_params.get("district") or ""

        qs = DistrictProfessionDemand.objects.filter(
            date__gte=date_from, date__lte=date_to
        ).select_related("profession")
        if district:
            qs = qs.filter(district__iexact=district)

        # Aggregate over the range per (district, profession)
        demand = defaultdict(int)        # (district, prof_name) -> summed demand
        supply = {}                      # prof_name -> latest available_masters
        districts, professions = [], []
        for row in qs:
            prof_name = row.profession.name
            demand[(row.district, prof_name)] += row.demand_count
            supply[prof_name] = max(supply.get(prof_name, 0), row.available_masters)
            if row.district not in districts:
                districts.append(row.district)
            if prof_name not in professions:
                professions.append(prof_name)

        districts.sort()
        professions.sort()

        cells = []
        for dist in districts:
            for prof in professions:
                d = demand.get((dist, prof), 0)
                s = supply.get(prof, 0)
                cells.append({
                    "district": dist,
                    "profession": prof,
                    "demand": d,
                    "available_masters": s,
                    "status": demand_status(d, s),
                })

        return Response({
            "range": {"from": str(date_from), "to": str(date_to)},
            "districts": districts,
            "professions": professions,
            "cells": cells,
        })