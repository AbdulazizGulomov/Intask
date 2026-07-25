# apps/accounts/views.py
import json
from functools import wraps

from django.conf import settings
from django.utils.safestring import mark_safe
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils.translation import get_language

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User, WorkerProfile
from apps.accounts.auth.otp import verify_otp, normalize_phone
from apps.jobs.models import Job, Profession
from apps.jobs.utils import format_pay


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


def user_can_work(user):
    """Whether the user may act as a worker (browse / apply to jobs).

    Single source of truth for the `can_work` capability also surfaced by
    _me_payload: a worker/employer role, or anyone who already has a
    WorkerProfile. `role` is only a UI mode flag, so a dual-capability user
    keeps this even while in employer mode.
    """
    role = getattr(user, "role", None)
    return role in ("worker", "employer") or getattr(user, "worker_profile", None) is not None


def user_can_hire(user):
    """Whether the user may post / manage jobs (hire).

    Single source of truth for the `can_hire` capability also surfaced by
    _me_payload: the stored can_hire flag, or an employer by default role.
    """
    role = getattr(user, "role", None)
    return bool(getattr(user, "can_hire", False)) or role == "employer"


_CAPABILITIES = {
    "can_work": user_can_work,
    "can_hire": user_can_hire,
}


def require_capability(*capabilities):
    """Gate a view on dual-mode capabilities (can_work / can_hire) instead of
    the raw role string.

    Unlike require_role, this does NOT lock a dual-capability user out of the
    "wrong" UI mode: a worker who switched to employer mode still satisfies
    can_work, and an employer-capable worker still satisfies can_hire. A user
    passes if they hold ANY of the requested capabilities. On failure it keeps
    require_role's response style (403 "Access denied"), so users who genuinely
    lack the capability see the same behavior as before.
    """
    checks = [_CAPABILITIES[c] for c in capabilities]  # KeyError = fail fast at import

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not (user.is_authenticated and any(check(user) for check in checks)):
                return HttpResponseForbidden("Access denied")

            # Keep session role synced like require_role, to avoid mode loops.
            role = getattr(user, "role", None) or request.session.get("user_role")
            if role:
                request.session["user_role"] = role
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def landing(request):
    return render(request, "landing.html")


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


def _profession_payload(prof):
    if not prof:
        return None
    return {
        "id": prof.id,
        "name": prof.name,
        "name_ru": prof.name_ru,
        "name_en": prof.name_en,
    }


def _me_payload(request):
    """Serialize the user + their WorkerProfile (existing fields only).

    Safe when the user has no WorkerProfile yet — those fields come back as
    null/empty rather than raising.
    """
    u = request.user
    wp = getattr(u, "worker_profile", None)

    photo_url = None
    if wp is not None and getattr(wp, "photo", None):
        try:
            photo_url = request.build_absolute_uri(wp.photo.url)
        except Exception:
            photo_url = None

    role = getattr(u, "role", None)
    # Derived dual-mode capabilities (computed, never stored). Same derivation
    # used by the require_capability decorator — see user_can_work/user_can_hire.
    can_work = user_can_work(u)
    can_hire = user_can_hire(u)

    return {
        "id": u.id,
        "phone": getattr(u, "phone", None),
        "role": role,
        "is_staff": u.is_staff,
        "first_name": getattr(wp, "first_name", "") or "",
        "last_name": getattr(wp, "last_name", "") or "",
        "full_name": getattr(wp, "full_name", "") or "",
        "gender": getattr(wp, "gender", None),
        "age": getattr(wp, "age", None),
        "profession": _profession_payload(getattr(wp, "profession", None)),
        "photo": photo_url,
        "can_work": can_work,
        "can_hire": can_hire,
    }


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def me(request):
    if request.method == "PATCH":
        # Create the profile on first edit if it doesn't exist yet.
        wp, _ = WorkerProfile.objects.get_or_create(user=request.user)
        data = request.data

        if "first_name" in data:
            wp.first_name = (data.get("first_name") or "").strip()
        if "last_name" in data:
            wp.last_name = (data.get("last_name") or "").strip()

        if "gender" in data:
            gender = data.get("gender")
            if gender in (None, ""):
                wp.gender = None
            elif gender in WorkerProfile.Gender.values:
                wp.gender = gender
            else:
                return Response(
                    {"gender": f"Invalid gender. Allowed: {list(WorkerProfile.Gender.values)}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if "age" in data:
            age = data.get("age")
            if age in (None, ""):
                wp.age = None
            else:
                try:
                    age_int = int(age)
                    if age_int < 0:
                        raise ValueError
                    wp.age = age_int
                except (TypeError, ValueError):
                    return Response(
                        {"age": "Age must be a non-negative integer."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        if "profession" in data:
            prof_id = data.get("profession")
            if prof_id in (None, ""):
                wp.profession = None
            else:
                try:
                    wp.profession = Profession.objects.get(pk=prof_id)
                except Profession.DoesNotExist:
                    return Response(
                        {"profession": "Invalid profession id."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                except (TypeError, ValueError):
                    return Response(
                        {"profession": "profession must be a numeric id."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # Photo upload (multipart/form-data with a "photo" file field).
        if "photo" in request.FILES:
            wp.photo = request.FILES["photo"]

        # Keep the derived full_name in sync when either name changed.
        if "first_name" in data or "last_name" in data:
            wp.full_name = f"{wp.first_name} {wp.last_name}".strip()

        wp.save()
        return Response(_me_payload(request))

    return Response(_me_payload(request))


@api_view(["POST", "PATCH"])
@permission_classes([IsAuthenticated])
def become_employer(request):
    """Enable hiring for the current user (dual-mode "Start hiring" action).

    Idempotent: flips can_hire on and returns the updated capabilities.
    """
    u = request.user
    if not u.can_hire:
        u.can_hire = True
        u.save(update_fields=["can_hire"])

    payload = _me_payload(request)
    return Response({"can_work": payload["can_work"], "can_hire": payload["can_hire"]})


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
    # Single source of truth lives in apps.jobs.utils.format_pay.
    return format_pay(job.pay_min, job.pay_max, job.pay_currency, getattr(job, "pay_text", ""))


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
@require_capability("can_work")
def worker_home(request):
    selected_regions = request.GET.getlist("region")
    selected_types = request.GET.getlist("type")
    selected_professions = request.GET.getlist("profession")
    q = (request.GET.get("q") or "").strip()

    region_label_map = dict(UZ_REGIONS)
    regions = [{"value": k, "label": v, "checked": k in selected_regions} for k, v in UZ_REGIONS]
    lang = get_language()
    professions = [
        {"value": str(p.id), "label": p.display_name(lang), "checked": str(p.id) in selected_professions}
        for p in Profession.objects.all().order_by("name")
    ]

    qs = Job.objects.filter(is_active=True)

    if selected_regions:
        qs = qs.filter(region__in=selected_regions)
    if selected_types:
        qs = qs.filter(job_type__in=selected_types)
    if selected_professions:
        qs = qs.filter(profession_id__in=selected_professions)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(region__icontains=q))

    qs = qs.order_by("-created_at")

    filtered_jobs = []
    for j in qs:
        region_label = region_label_map.get(j.region, j.region)
        type_label = j.get_job_type_display() if hasattr(j, "get_job_type_display") else j.job_type

        detail_url = reverse("jobs:detail", args=[j.id])  # ✅ ALWAYS BUILD HERE

        filtered_jobs.append(
            {
                "id": j.id,
                "title": j.title,
                "region": j.region,
                "region_label": region_label,
                "type": j.job_type,
                "type_label": type_label,
                "pay": _pay_display(j),
                "lat": j.lat,
                "lng": j.lng,
                "photo_url": _first_photo_url(j),
                "detail_url": detail_url,  # ✅ for card click
            }
        )

    selected_region_labels = [region_label_map.get(r, r) for r in selected_regions]

    # ✅ IMPORTANT: include detail_url in jobs_map too (for Yandex map balloon)
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
                    "type": j["type"],            # raw key (hourly/daily) for the badge style
                    "job_type": j["type_label"],  # display label for the badge text
                    "detail_url": j["detail_url"],  # ✅ map uses this
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
            "job_type_choices": Job.JobType.choices,  # drive the "Ish turi" filter from the model
            "q": q,
            "jobs_map": mark_safe(json.dumps(jobs_map)),
        },
    )


@login_required
@require_capability("can_hire")
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
@require_capability("can_hire")
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

    ok, err = verify_otp(phone, code)
    if not ok:
        return render(request, "otp.html", {"error": err or "Invalid or expired code", "next": next_url})

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

    # Land back on the home page (/) by default, honoring only a safe, same-host
    # ?next=. Requirement: login never dumps the user on role-select/login.
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = settings.LOGIN_REDIRECT_URL

    if user.role == "worker":
        profile, _ = WorkerProfile.objects.get_or_create(user=user)
        if not profile.is_completed:
            # First-time worker: finish the profile, then continue to `next`.
            return redirect(f"{reverse('accounts:worker_register')}?next={next_url}")

    return redirect(next_url)


@login_required
@require_role("worker")
def worker_register(request):
    profile, _ = WorkerProfile.objects.get_or_create(user=request.user)

    # After registration, continue to a safe, same-host ?next= (carried through
    # the form), else the home page (/). Never back to role-select/login.
    next_url = request.POST.get("next") or request.GET.get("next") or settings.LOGIN_REDIRECT_URL
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = settings.LOGIN_REDIRECT_URL

    if profile.is_completed:
        return redirect(next_url)

    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        age_raw = (request.POST.get("age") or "").strip()
        gender = (request.POST.get("gender") or "").strip()

        ctx = {"profile": profile, "next": next_url}
        if not first_name or not last_name or not age_raw or not gender:
            return render(request, "worker_register.html", {**ctx, "error": "All fields are required"})

        try:
            age = int(age_raw)
        except ValueError:
            return render(request, "worker_register.html", {**ctx, "error": "Age must be a number"})

        profile.first_name = first_name
        profile.last_name = last_name
        profile.age = age
        profile.gender = gender

        photo = request.FILES.get("photo")
        if photo:
            profile.photo = photo

        profile.is_completed = True
        profile.save()

        return redirect(next_url)

    return render(request, "worker_register.html", {"profile": profile, "next": next_url})


def after_otp_redirect(request):
    """Post-login gate hit by the OTP web flow (templates/otp.html → the API
    verify view returns this URL).

    Requirement: after a successful login/registration the user lands on the
    public home page (/), which now renders their logged-in header — NOT the
    role-selection screen or a forced role dashboard. We still honor a safe,
    same-host ?next= (e.g. a deep link the user was trying to reach) and still
    make a first-time worker finish their profile before continuing.
    """
    if not request.user.is_authenticated:
        return redirect("accounts:role_select")

    next_url = request.GET.get("next") or settings.LOGIN_REDIRECT_URL

    # Only honor local, same-host paths; external targets fall back to home.
    if not url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()},
            require_https=request.is_secure()):
        next_url = settings.LOGIN_REDIRECT_URL

    # First-time worker: finish the profile first, then continue to `next`.
    role = getattr(request.user, "role", None) or request.session.get("user_role") or ""
    if role == "worker":
        profile, _ = WorkerProfile.objects.get_or_create(user=request.user)
        if not profile.is_completed:
            return redirect(f"{reverse('accounts:worker_register')}?next={next_url}")

    # Everyone lands on their intended page, defaulting to the home page (/).
    return redirect(next_url)


def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect(reverse("accounts:role_select"))