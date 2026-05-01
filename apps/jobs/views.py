from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from apps.accounts.views import require_role, UZ_REGIONS
from .models import Job, Profession, JobApplication
from utils.translations import t


@login_required
def worker_job_detail(request, job_id: int):
    preview = request.GET.get("preview") == "1"
    edit_mode = request.GET.get("edit") == "1"
    role = getattr(request.user, "role", None)

    if role not in ["worker", "employer"]:
        return HttpResponseForbidden("Access denied")

    job = get_object_or_404(Job, id=job_id, is_active=True)

    # Employer can only access own job
    if role == "employer":
        if job.employer != request.user:
            return HttpResponseForbidden("Access denied")

    # Employer preview edit mode
    if preview and request.method == "POST" and role == "employer":
        job.title = (request.POST.get("title") or "").strip()
        job.region = (request.POST.get("region") or "").strip()
        job.job_type = (request.POST.get("job_type") or "").strip()
        job.description = (request.POST.get("description") or "").strip()
        job.contact_phone = (request.POST.get("contact_phone") or "").strip()
        job.pay_text = (request.POST.get("pay_text") or "").strip()

        profession_id = (request.POST.get("profession") or "").strip()
        if profession_id:
            profession = Profession.objects.filter(id=profession_id).first()
            if profession:
                job.profession = profession

        lat_raw = (request.POST.get("lat") or "").strip()
        lng_raw = (request.POST.get("lng") or "").strip()

        def to_float(v: str):
            if not v:
                return None
            try:
                return float(v.replace(",", "."))
            except ValueError:
                return None

        job.lat = to_float(lat_raw)
        job.lng = to_float(lng_raw)

        for i in range(1, 5):
            photo_field = f"photo{i}"
            delete_field = f"delete_photo{i}"

            if request.POST.get(delete_field) == "on":
                old_photo = getattr(job, photo_field)
                if old_photo:
                    old_photo.delete(save=False)
                    setattr(job, photo_field, None)

            if photo_field in request.FILES:
                setattr(job, photo_field, request.FILES[photo_field])

        job.save()
        return redirect(f"/worker/job/{job.id}/?preview=1")

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

    region_choices = UZ_REGIONS
    job_type_choices = Job.JobType.choices
    professions = Profession.objects.all().order_by("name")
    profession_name = job.profession.name if getattr(job, "profession", None) else ""

    applicants = []
    already_applied = False

    if role == "employer":
        applicants = (
            JobApplication.objects
            .filter(job=job)
            .select_related("worker", "worker__worker_profile")
            .order_by("-created_at")
        )

    if role == "worker":
        already_applied = JobApplication.objects.filter(job=job, worker=request.user).exists()

    ctx = {
        "job": job,
        "region_label": region_label,
        "pay_display": pay_display,
        "photos": photos,
        "preview_mode": preview,
        "edit_mode": edit_mode,
        "region_choices": region_choices,
        "job_type_choices": job_type_choices,
        "professions": professions,
        "profession_name": profession_name,
        "applicants": applicants,
        "already_applied": already_applied,
        "is_employer_view": role == "employer",
        "is_worker_view": role == "worker",
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

    professions = Profession.objects.all().order_by("name")

    base_ctx = {
        "regions": UZ_REGIONS,
        "job_types": Job.JobType.choices,
        "currencies": currencies,
        "professions": professions,
    }

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        region = (request.POST.get("region") or "").strip()
        job_type = (request.POST.get("job_type") or "").strip()
        profession_id = (request.POST.get("profession") or "").strip()

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

        profession = None
        if profession_id:
            profession = Profession.objects.filter(id=profession_id).first()

        if not title or not region or not job_type or not profession:
            ctx = {
                **base_ctx,
                "error": t("job_required_fields_error"),
            }
            return render(request, "employer_job_create.html", ctx)

        try:
            pay_min = to_decimal(pay_min_raw)
            pay_max = to_decimal(pay_max_raw)
        except (InvalidOperation, ValueError):
            ctx = {**base_ctx, "error": t("pay_must_be_numbers")}
            return render(request, "employer_job_create.html", ctx)

        if pay_min is not None and pay_max is not None and pay_min > pay_max:
            ctx = {**base_ctx, "error": t("pay_min_invalid")}
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
            profession=profession,
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


@login_required
@require_role("employer")
def employer_job_edit(request, pk):
    job = get_object_or_404(Job, id=pk, employer=request.user)

    currencies = (
        Job.Currency.choices
        if hasattr(Job, "Currency")
        else [("UZS", "UZS"), ("USD", "USD")]
    )

    professions = Profession.objects.all().order_by("name")

    ctx = {
        "job": job,
        "regions": UZ_REGIONS,
        "job_types": Job.JobType.choices,
        "currencies": currencies,
        "professions": professions,
    }

    if request.method == "POST":
        job.title = (request.POST.get("title") or "").strip()
        job.region = (request.POST.get("region") or "").strip()
        job.job_type = (request.POST.get("job_type") or "").strip()
        job.pay_currency = (request.POST.get("pay_currency") or "UZS").strip()
        job.pay_text = (request.POST.get("pay_text") or "").strip()
        job.description = (request.POST.get("description") or "").strip()
        job.contact_phone = (request.POST.get("contact_phone") or "").strip()

        profession_id = (request.POST.get("profession") or "").strip()
        if profession_id:
            profession = Profession.objects.filter(id=profession_id).first()
            if profession:
                job.profession = profession

        job.save()
        return redirect("accounts:employer_home")

    return render(request, "employer_job_edit.html", ctx)