from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from apps.accounts.views import require_role, UZ_REGIONS
from .models import Job


@login_required
def worker_job_detail(request, job_id: int):
    preview = request.GET.get("preview") == "1"

    if request.user.role != "worker" and not preview:
        return HttpResponseForbidden("Access denied")

    job = get_object_or_404(Job, id=job_id, is_active=True)

    region_label_map = dict(UZ_REGIONS)
    region_label = region_label_map.get(job.region, job.region)

    pay_display = ""
    if job.pay_min is not None and job.pay_max is not None:
        pay_display = f"{job.pay_min:g}–{job.pay_max:g} {job.pay_currency}"
    elif job.pay_min is not None:
        pay_display = f"{job.pay_min:g}+ {job.pay_currency}"
    elif job.pay_max is not None:
        pay_display = f"≤ {job.pay_max:g} {job.pay_currency}"
    elif getattr(job, "pay_text", ""):
        pay_display = job.pay_text

    photos = []
    if job.photo1:
        photos.append(job.photo1)
    if job.photo2:
        photos.append(job.photo2)
    if job.photo3:
        photos.append(job.photo3)
    if job.photo4:
        photos.append(job.photo4)

    ctx = {
        "job": job,
        "region_label": region_label,
        "pay_display": pay_display,
        "photos": photos,
        "preview_mode": preview,
    }

    return render(request, "worker_job_detail.html", ctx)


@login_required
def job_detail(request, pk: int):
    return worker_job_detail(request, job_id=pk)


@login_required
@require_role("employer")
def employer_job_create(request):
    def to_decimal(v: str):
        if not v:
            return None
        v = v.replace(",", ".")
        return Decimal(v)

    currencies = (
        Job.Currency.choices
        if hasattr(Job, "Currency")
        else [("UZS", "UZS"), ("USD", "USD")]
    )

    base_ctx = {
        "regions": UZ_REGIONS,
        "job_types": Job.JobType.choices,
        "currencies": currencies,
    }

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        region = (request.POST.get("region") or "").strip()
        job_type = (request.POST.get("job_type") or "").strip()

        pay_currency = (request.POST.get("pay_currency") or "UZS").strip()
        pay_min_raw = (request.POST.get("pay_min") or "").strip()
        pay_max_raw = (request.POST.get("pay_max") or "").strip()
        pay_text = (request.POST.get("pay_text") or "").strip()

        description = (request.POST.get("description") or "").strip()
        contact_phone = (request.POST.get("contact_phone") or "").strip()
        lat = (request.POST.get("lat") or "").strip()
        lng = (request.POST.get("lng") or "").strip()

        photo1 = request.FILES.get("photo1")
        photo2 = request.FILES.get("photo2")
        photo3 = request.FILES.get("photo3")
        photo4 = request.FILES.get("photo4")

        if not title or not region or not job_type:
            ctx = {**base_ctx, "error": "Title, region, and job type are required."}
            return render(request, "employer_job_create.html", ctx)

        try:
            pay_min = to_decimal(pay_min_raw)
            pay_max = to_decimal(pay_max_raw)
        except (InvalidOperation, ValueError):
            ctx = {**base_ctx, "error": "Pay min/max must be numbers."}
            return render(request, "employer_job_create.html", ctx)

        if pay_min is not None and pay_max is not None and pay_min > pay_max:
            ctx = {**base_ctx, "error": "Pay min cannot be greater than pay max."}
            return render(request, "employer_job_create.html", ctx)

        def to_float(v: str):
            if not v:
                return None
            try:
                return float(v.replace(",", "."))
            except ValueError:
                return None

        Job.objects.create(
            employer=request.user,
            title=title,
            region=region,
            job_type=job_type,
            pay_currency=pay_currency,
            pay_min=pay_min,
            pay_max=pay_max,
            pay_text=pay_text,
            description=description,
            contact_phone=contact_phone,
            lat=to_float(lat),
            lng=to_float(lng),
            photo1=photo1,
            photo2=photo2,
            photo3=photo3,
            photo4=photo4,
            is_active=True,
        )

        return redirect("accounts:employer_home")

    return render(request, "employer_job_create.html", base_ctx)
