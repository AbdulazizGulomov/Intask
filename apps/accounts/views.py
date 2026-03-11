# apps/accounts/views.py
import json
from functools import wraps

from django.utils.safestring import mark_safe
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User, WorkerProfile
from apps.accounts.auth.otp import verify_otp, normalize_phone
from apps.jobs.models import Job, Profession


ALLOWED_ROLES = {"worker", "employer"}

UZ_REGIONS = [
    ("toshkent_city", "Toshkent shahri"),
    ("toshkent", "Toshkent viloyati"),
    ("andijon", "Andijon"),
    ("fargona", "Farg‘ona"),
    ("namangan", "Namangan"),
    ("samarqand", "Samarqand"),
    ("buxoro", "Buxoro"),
    ("navoiy", "Navoiy"),
    ("qashqadaryo", "Qashqadaryo"),
    ("surxondaryo", "Surxondaryo"),
    ("xorazm", "Xorazm"),
    ("jizzax", "Jizzax"),
    ("sirdaryo", "Sirdaryo"),
    ("qoraqalpogiston", "Qoraqalpog‘iston"),
]


def require_role(*allowed_roles):
    """
    Uses request.user.role first (if authenticated), then session fallback.
    Keeps session role synced to avoid Access denied loops.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            role = None

            if request.user.is_authenticated:
                role = getattr(request.user, "role", None)

            if not role:
                role = request.session.get("user_role")

            if role not in allowed_roles:
                return HttpResponseForbidden("Access denied")

            request.session["user_role"] = role
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def role_select(request):
    return render(request, "role_select.html")


def choose_role(request, role):
    role = (role or "").lower().strip()
    if role not in ALLOWED_ROLES:
        return HttpResponseBadRequest(f"Invalid role: {role}")

    request.session["user_role"] = role
    next_url = reverse("accounts:worker_home") if role == "worker" else reverse("accounts:employer_home")

    if request.user.is_authenticated:
        if getattr(request.user, "role", None) != role:
            request.user.role = role
            request.user.save(update_fields=["role"])
        request.session["user_role"] = role
        return redirect(next_url)

    return redirect(f"{reverse('accounts:otp')}?next={next_url}")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    return Response(
        {
            "id": u.id,
            "phone": getattr(u, "phone", None),
            "role": getattr(u, "role", None),
            "session_role": request.session.get("user_role"),
            "is_staff": u.is_staff,
        }
    )


def require_login_for_apply(request):
    if not request.user.is_authenticated:
        next_url = request.GET.get("next") or reverse("accounts:worker_home")
        return redirect(f"{reverse('accounts:otp')}?next={next_url}")
    return redirect("accounts:worker_home")


def _first_photo_url(job: Job):
    if getattr(job, "photo1", None):
        return job.photo1.url
    if getattr(job, "photo2", None):
        return job.photo2.url
    if getattr(job, "photo3", None):
        return job.photo3.url
    if getattr(job, "photo4", None):
        return job.photo4.url
    return None


def _pay_display(job: Job) -> str:
    try:
        if job.pay_min is not None and job.pay_max is not None:
            return f"{job.pay_min:g}–{job.pay_max:g} {job.pay_currency}"
        if job.pay_min is not None:
            return f"{job.pay_min:g}+ {job.pay_currency}"
        if job.pay_max is not None:
            return f"≤ {job.pay_max:g} {job.pay_currency}"
        if getattr(job, "pay_text", None):
            return job.pay_text or ""
    except Exception:
        pass
    return ""


def get_display_name(user) -> str:
    if not user or not getattr(user, "is_authenticated", False):
        return "Foydalanuvchi"

    if getattr(user, "role", None) == "worker":
        try:
            wp = user.worker_profile
            name = (getattr(wp, "full_name", "") or f"{wp.first_name} {wp.last_name}".strip()).strip()
            if name:
                return name
        except Exception:
            pass

    return getattr(user, "phone", None) or getattr(user, "username", None) or "Foydalanuvchi"


@login_required
@require_role("worker")
def worker_home(request):
    selected_regions = request.GET.getlist("region")
    selected_types = request.GET.getlist("type")
    selected_professions = request.GET.getlist("profession")
    q = (request.GET.get("q") or "").strip()

    region_label_map = dict(UZ_REGIONS)
    regions = [{"value": k, "label": v, "checked": k in selected_regions} for k, v in UZ_REGIONS]

    professions = Profession.objects.all().order_by("name")

    qs = Job.objects.filter(is_active=True).select_related("profession")

    if selected_regions:
        qs = qs.filter(region__in=selected_regions)
    if selected_types:
        qs = qs.filter(job_type__in=selected_types)
    if selected_professions:
        qs = qs.filter(profession_id__in=selected_professions)
    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(region__icontains=q) |
            Q(profession__name__icontains=q)
        )

    qs = qs.order_by("-created_at")

    filtered_jobs = []
    for j in qs:
        region_label = region_label_map.get(j.region, j.region)
        type_label = j.get_job_type_display() if hasattr(j, "get_job_type_display") else j.job_type
        profession_name = j.profession.name if getattr(j, "profession", None) else ""

        detail_url = reverse("jobs:detail", args=[j.id])

        filtered_jobs.append(
            {
                "id": j.id,
                "title": j.title,
                "region": j.region,
                "region_label": region_label,
                "type": j.job_type,
                "type_label": type_label,
                "profession_name": profession_name,
                "pay": _pay_display(j),
                "lat": j.lat,
                "lng": j.lng,
                "photo_url": _first_photo_url(j),
                "detail_url": detail_url,
            }
        )

    selected_region_labels = [region_label_map.get(r, r) for r in selected_regions]

    jobs_map = []
    for j in filtered_jobs:
        if j.get("lat") is not None and j.get("lng") is not None:
            jobs_map.append(
                {
                    "id": j["id"],
                    "title": j["title"],
                    "pay": j["pay"],
                    "lat": j["lat"],
                    "lng": j["lng"],
                    "region_label": j["region_label"],
                    "job_type": j["type_label"],
                    "profession_name": j["profession_name"],
                    "detail_url": j["detail_url"],
                }
            )

    return render(
        request,
        "worker_home.html",
        {
            "display_name": get_display_name(request.user),
            "regions": regions,
            "professions": professions,
            "jobs": filtered_jobs,
            "selected_regions": selected_regions,
            "selected_region_labels": selected_region_labels,
            "selected_types": selected_types,
            "selected_professions": selected_professions,
            "q": q,
            "jobs_map": mark_safe(json.dumps(jobs_map)),
        },
    )


@login_required
@require_role("employer")
def employer_home(request):
    jobs = Job.objects.filter(employer=request.user).order_by("-created_at")
    region_label_map = dict(UZ_REGIONS)

    items = []
    for j in jobs:
        items.append(
            {
                "id": j.id,
                "title": j.title,
                "region": j.region,
                "region_label": region_label_map.get(j.region, j.region),
                "type": j.job_type,
                "type_label": j.get_job_type_display() if hasattr(j, "get_job_type_display") else j.job_type,
                "pay": _pay_display(j),
                "is_active": j.is_active,
                "created_at": j.created_at,
                "photo_url": _first_photo_url(j),
                "detail_url": reverse("jobs:detail", args=[j.id]),
            }
        )

    return render(
        request,
        "employer_home.html",
        {"display_name": get_display_name(request.user), "jobs": items},
    )


@login_required
@require_role("employer")
def workers_base(request):
    selected = set(request.GET.getlist("cat"))
    categories = [
        {"value": "mavsumi Ishchi", "label": "Mavsumiy Ishchi", "checked": "mavsumi Ishchi" in selected},
        {"value": "santexnik", "label": "Santexnik", "checked": "santexnik" in selected},
        {"value": "elektrik", "label": "Elektrik", "checked": "elektrik" in selected},
        {"value": "quruvchi", "label": "Quruvchi", "checked": "quruvchi" in selected},
        {"value": "haydovchi", "label": "Haydovchi", "checked": "haydovchi" in selected},
        {"value": "tozalovchi", "label": "Tozalovchi", "checked": "tozalovchi" in selected},
    ]
    workers = [
        {"rank": 1, "rank_color": "gold", "full_name": "Jasurbek", "profession": "Elektrik", "rating": "4.9", "phone": "+998901112233", "is_top": True},
        {"rank": 2, "rank_color": "silver", "full_name": "Akmalbek", "profession": "Santexnik", "rating": "4.9", "phone": "+998909998877", "is_top": False},
    ]
    return render(request, "workers_base.html", {"categories": categories, "workers": workers, "active_chips": None})


def otp_login(request):
    next_url = request.GET.get("next") or "/"
    return render(request, "otp.html", {"next": next_url})


def otp_verify_web(request):
    if request.method != "POST":
        return redirect("accounts:otp")

    phone = normalize_phone(request.POST.get("phone", ""))
    code = (request.POST.get("code") or "").strip()
    next_url = request.POST.get("next") or "/"

    if not verify_otp(phone, code):
        return render(request, "otp.html", {"error": "Invalid or expired code", "next": next_url})

    role = request.session.get("user_role") or "worker"

    user, created = User.objects.get_or_create(
        phone=phone,
        defaults={"role": role, "is_active": True},
    )

    if (not created) and role in ("worker", "employer") and user.role != role:
        user.role = role
        user.save(update_fields=["role"])

    user.backend = "django.contrib.auth.backends.ModelBackend"
    login(request, user)
    request.session["user_role"] = user.role

    if user.role == "worker":
        profile, _ = WorkerProfile.objects.get_or_create(user=user)
        if not profile.is_completed:
            return redirect("accounts:worker_register")

    return redirect(
        next_url
        or (reverse("accounts:worker_home") if user.role == "worker" else reverse("accounts:employer_home"))
    )


@login_required
@require_role("worker")
def worker_register(request):
    profile, _ = WorkerProfile.objects.get_or_create(user=request.user)

    if profile.is_completed:
        return redirect("accounts:worker_home")

    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        age_raw = (request.POST.get("age") or "").strip()
        gender = (request.POST.get("gender") or "").strip()

        if not first_name or not last_name or not age_raw or not gender:
            return render(request, "worker_register.html", {"error": "All fields are required", "profile": profile})

        try:
            age = int(age_raw)
        except ValueError:
            return render(request, "worker_register.html", {"error": "Age must be a number", "profile": profile})

        profile.first_name = first_name
        profile.last_name = last_name
        profile.age = age
        profile.gender = gender

        photo = request.FILES.get("photo")
        if photo:
            profile.photo = photo

        profile.is_completed = True
        profile.save()

        return redirect("accounts:worker_home")

    return render(request, "worker_register.html", {"profile": profile})


def after_otp_redirect(request):
    if not request.user.is_authenticated:
        return redirect("accounts:role_select")

    next_url = request.GET.get("next") or "/"

    if request.user.role == "worker":
        profile, _ = WorkerProfile.objects.get_or_create(user=request.user)
        if not profile.is_completed:
            return redirect("accounts:worker_register")

    return redirect(next_url)


def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect(reverse("accounts:role_select"))