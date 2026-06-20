# apps/analytics/utils.py
"""Shared helpers for the analytics rollups and endpoints."""
from datetime import date, timedelta

UNKNOWN_DISTRICT = "Unknown"


def district_from_address(address: str) -> str:
    """
    Derive a district label from an order address.

    Mirrors the convention already used by the dashboard's
    RevenueByDistrictChartView: seed addresses look like
    "Yunusobod district, Tashkent" -> "Yunusobod".
    """
    address = (address or "").strip()
    if not address:
        return UNKNOWN_DISTRICT
    return address.split()[0].strip(",") or UNKNOWN_DISTRICT


def parse_date(value, fallback):
    """Parse a YYYY-MM-DD query param; return `fallback` on missing/invalid."""
    if not value:
        return fallback
    try:
        y, m, d = str(value).split("-")
        return date(int(y), int(m), int(d))
    except (ValueError, AttributeError):
        return fallback


def resolve_range(request, default_days=30):
    """
    Resolve (date_from, date_to) from ?from=&to= query params.

    Defaults to the last `default_days` days (inclusive). Always returns a
    valid, ordered pair so endpoints never 500 on bad input.
    """
    today = date.today()
    date_to = parse_date(request.query_params.get("to"), today)
    date_from = parse_date(
        request.query_params.get("from"), date_to - timedelta(days=default_days - 1)
    )
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def previous_range(date_from, date_to):
    """The immediately-preceding window of equal length, for deltas."""
    span = (date_to - date_from).days + 1
    prev_to = date_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=span - 1)
    return prev_from, prev_to


def pct_delta(current, previous):
    """Percent change vs previous period. None when previous is zero/empty."""
    if previous in (None, 0):
        return None
    return round((float(current) - float(previous)) / float(previous) * 100, 1)


def demand_status(demand_count, available_masters):
    """Classify a (demand, supply) pair into ok / tight / gap."""
    from .models import DistrictProfessionDemand

    if available_masters <= 0:
        return (
            DistrictProfessionDemand.Status.GAP
            if demand_count > 0
            else DistrictProfessionDemand.Status.OK
        )
    ratio = demand_count / available_masters
    if ratio > 1:
        return DistrictProfessionDemand.Status.GAP
    if ratio >= 0.6:
        return DistrictProfessionDemand.Status.TIGHT
    return DistrictProfessionDemand.Status.OK