# apps/jobs/utils.py
"""Display-only pay formatting. Never alters stored Decimal values."""
from decimal import Decimal, InvalidOperation

from django.utils.translation import gettext as _


def _grouped(amount, sep):
    """Amount as grouped digits using `sep` for thousands.
    Whole numbers drop decimals; fractional values keep 2 places."""
    try:
        d = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        return ""
    if d == d.to_integral_value():
        s = "{:,}".format(int(d))
    else:
        s = "{:,.2f}".format(d)
    return s.replace(",", sep)


def _one(amount, currency):
    """A single amount: "6 000 000 so'm" (UZS) or "$1,500" (USD)."""
    if amount is None:
        return ""
    if currency == "USD":
        return "$" + _grouped(amount, ",")
    return "{} {}".format(_grouped(amount, " "), _("so'm"))


def format_pay(pay_min, pay_max, currency="UZS", pay_text=""):
    """Human-readable pay for a job. Display-only; prefers the pay_text override."""
    text = (pay_text or "").strip()
    if text:
        return text

    currency = currency or "UZS"

    if pay_min is not None and pay_max is not None and pay_min != pay_max:
        if currency == "USD":
            return "{} – {}".format(_one(pay_min, "USD"), _one(pay_max, "USD"))
        # UZS: group both, suffix once → "6 000 000 – 8 000 000 so'm"
        return "{} – {} {}".format(_grouped(pay_min, " "), _grouped(pay_max, " "), _("so'm"))

    single = pay_min if pay_min is not None else pay_max
    return _one(single, currency)  # "" when both are None — no "None so'm"


# Plausibility ceilings per period, in so'm. Above these an amount is far more
# likely a mismatched period (e.g. a monthly salary tagged "Hourly") than a real
# rate. Tunable; UZS-only because the numbers are so'm-scaled.
PAY_WARN_CEILING_UZS = {
    "hourly": Decimal("500000"),
    "daily": Decimal("5000000"),
}


def pay_period_warning(pay_min, pay_max, job_type, currency="UZS"):
    """A soft "did you mean a different period?" nudge, or "" when the amount is
    plausible. NEVER raises and NEVER blocks — callers surface the string as a
    warning, not an error.

    Only so'm amounts are judged (USD amounts are left alone, since the ceilings
    are so'm-scaled). The larger of pay_min/pay_max is compared to the ceiling
    for the selected period.
    """
    if (currency or "UZS") != "UZS":
        return ""

    period = (job_type or "").strip().lower()
    ceiling = PAY_WARN_CEILING_UZS.get(period)
    if ceiling is None:  # no ceiling defined for this period (e.g. blank) → no nudge
        return ""

    amounts = []
    for a in (pay_min, pay_max):
        if a is None:
            continue
        try:
            amounts.append(Decimal(str(a)))
        except (InvalidOperation, TypeError, ValueError):
            continue
    if not amounts:
        return ""

    top = max(amounts)
    if top <= ceiling:
        return ""

    period_label = {"hourly": _("hourly"), "daily": _("daily")}.get(period, period)
    return _(
        "%(amount)s so'm looks high for an %(period)s rate — did you mean a "
        "different pay period?"
    ) % {"amount": _grouped(top, " "), "period": period_label}
