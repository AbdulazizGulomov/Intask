# apps/jobs/api.py
from decimal import Decimal, InvalidOperation

from rest_framework import serializers, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Avg, Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from apps.jobs.models import Job, JobApplication, Profession
from apps.jobs.utils import format_pay, pay_period_warning, haversine_km
from apps.moderation.filters import REJECTION_MESSAGE, contains_banned_words
from apps.moderation.selectors import blocked_user_ids, is_blocked_between
from apps.orders.models import Order


class JobListSerializer(serializers.ModelSerializer):
    cover = serializers.SerializerMethodField()
    pay = serializers.SerializerMethodField()
    profession = serializers.SerializerMethodField()
    # Privacy gating: contact details are hidden from logged-out users.
    contact_phone = serializers.SerializerMethodField()
    contact_visible = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id", "title", "region", "job_type", "profession",
            "pay_currency", "pay_min", "pay_max", "pay_text", "pay",
            "cover", "lat", "lng", "address",
            "district", "street", "house", "landmark", "created_at",
            "contact_phone", "contact_visible", "workers_needed",
        ]

    def _is_authenticated(self):
        request = self.context.get("request")
        return bool(request and request.user and request.user.is_authenticated)

    def get_contact_phone(self, obj):
        # Only logged-in users see the contact phone.
        if self._is_authenticated():
            return obj.contact_phone
        return None

    def get_contact_visible(self, obj):
        # Lets the app decide whether to show a "login to see contact" prompt.
        return self._is_authenticated()

    def get_profession(self, obj):
        if obj.profession_id:
            p = obj.profession
            return {
                "id": p.id,
                "name": p.name,          # Uzbek default
                "name_ru": p.name_ru,
                "name_en": p.name_en,
            }
        return None

    def get_cover(self, obj):
        request = self.context.get("request")
        for field in ("photo1", "photo2", "photo3", "photo4"):
            img = getattr(obj, field, None)
            if img:
                url = img.url
                return request.build_absolute_uri(url) if request else url
        return None

    def get_pay(self, obj):
        # Single source of truth — same formatter the web views use, so web and
        # mobile render an identical string (incl. the pay_text override).
        return format_pay(obj.pay_min, obj.pay_max, obj.pay_currency, getattr(obj, "pay_text", ""))


class JobDetailSerializer(JobListSerializer):
    photos = serializers.SerializerMethodField()
    # Employer-side "1 / 2 o'rin to'ldi": accepted applications for this job.
    accepted_count = serializers.SerializerMethodField()

    class Meta(JobListSerializer.Meta):
        # lat/lng now come from JobListSerializer.Meta.fields (added for the list);
        # only the detail-only fields are appended here.
        fields = JobListSerializer.Meta.fields + [
            "description", "contact_phone", "photos", "accepted_count",
        ]

    def get_accepted_count(self, obj):
        return obj.applications.filter(status=JobApplication.Status.ACCEPTED).count()

    def get_photos(self, obj):
        request = self.context.get("request")
        out = []
        for field in ("photo1", "photo2", "photo3", "photo4"):
            img = getattr(obj, field, None)
            if img:
                url = img.url
                out.append(request.build_absolute_uri(url) if request else url)
        return out


class JobsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class JobListAPIView(generics.ListAPIView):
    serializer_class = JobListSerializer
    permission_classes = [AllowAny]
    pagination_class = JobsPagination

    def get_queryset(self):
        qs = (
            Job.objects.filter(is_active=True)
            .select_related("profession")
            .order_by("-created_at")
        )
        region = self.request.query_params.get("region")
        job_type = self.request.query_params.get("job_type")
        search = self.request.query_params.get("search")
        profession = self.request.query_params.get("profession")
        if region:
            qs = qs.filter(region=region)
        if job_type:
            qs = qs.filter(job_type=job_type)
        if search:
            qs = qs.filter(title__icontains=search)
        if profession:
            qs = qs.filter(profession_id=profession)
        # UGC safety: a block hides each party's listings from the other, in
        # both directions. No-op for anonymous callers.
        blocked = blocked_user_ids(self.request.user)
        if blocked:
            qs = qs.exclude(employer_id__in=blocked)
        return qs


class JobDetailAPIView(generics.RetrieveAPIView):
    serializer_class = JobDetailSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Job.objects.filter(is_active=True).select_related("profession")
        # 404 rather than 403 for a blocked employer's job: the listing should
        # look absent, not merely forbidden.
        blocked = blocked_user_ids(self.request.user)
        return qs.exclude(employer_id__in=blocked) if blocked else qs


class JobApplyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, is_active=True)
        user = request.user
        # Blocked in either direction -> the job is invisible to this user, so
        # applying must fail the same way browsing does.
        if job.employer_id and is_blocked_between(user, job.employer_id):
            raise Http404
        # Capability-based gate (dual-mode): allow anyone who can work — worker/
        # employer role, or anyone with a WorkerProfile. Only pure non-worker
        # roles (operator/admin) are blocked.
        can_work = (
            getattr(user, "role", None) in ("worker", "employer")
            or hasattr(user, "worker_profile")
        )
        if not can_work:
            return Response(
                {"detail": "Only workers can apply to jobs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        application, created = JobApplication.objects.get_or_create(
            job=job, worker=user, defaults={"employer": job.employer},
        )
        return Response(
            {
                "id": application.id,
                "job": job.id,
                "status": application.status,
                "already_applied": not created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class JobCreateAPIView(APIView):
    """Employer creates a job from the mobile app.

    Mirrors the field semantics of the web `employer_job_create` view, but
    photos are optional here (the web form requires 1-4). Any authenticated
    user may post for now — see report note on the role check.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @staticmethod
    def _to_decimal(v):
        if v in (None, ""):
            return None
        return Decimal(str(v).replace(",", "."))

    @staticmethod
    def _to_float(v):
        if v in (None, ""):
            return None
        try:
            return float(str(v).replace(",", "."))
        except (TypeError, ValueError):
            return None

    def post(self, request):
        data = request.data

        title = (str(data.get("title") or "")).strip()
        region = (str(data.get("region") or "")).strip()
        job_type = (str(data.get("job_type") or "")).strip()

        # Required fields.
        errors = {}
        if not title:
            errors["title"] = "This field is required."
        if not region:
            errors["region"] = "This field is required."
        if not job_type:
            errors["job_type"] = "This field is required."
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # UGC safety: reject banned language in the two free-text fields before
        # anything is written. Errors are keyed per field so the app can point
        # at the offending input; the message never echoes the matched word.
        description_raw = str(data.get("description") or "")
        content_errors = {}
        if contains_banned_words(title):
            content_errors["title"] = [str(REJECTION_MESSAGE)]
        if contains_banned_words(description_raw):
            content_errors["description"] = [str(REJECTION_MESSAGE)]
        if content_errors:
            return Response(content_errors, status=status.HTTP_400_BAD_REQUEST)

        # Profession is optional; keep only a valid existing id, else leave unset
        # (same lenient behavior as the web view).
        profession_id = None
        prof_raw = data.get("profession")
        if prof_raw not in (None, ""):
            prof_str = str(prof_raw).strip()
            if prof_str.isdigit() and Profession.objects.filter(id=prof_str).exists():
                profession_id = int(prof_str)

        # Currency: default UZS, coerce unknown to the safe default (no error).
        pay_currency = (str(data.get("pay_currency") or "UZS")).strip()
        if pay_currency not in {c[0] for c in Job.Currency.choices}:
            pay_currency = Job.Currency.UZS

        try:
            pay_min = self._to_decimal(data.get("pay_min"))
            pay_max = self._to_decimal(data.get("pay_max"))
        except (InvalidOperation, ValueError):
            return Response(
                {"pay": "Pay min/max must be numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if pay_min is not None and pay_max is not None and pay_min > pay_max:
            return Response(
                {"pay": "Pay min cannot be greater than pay max."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Workers needed: optional, defaults to 1, must be a positive integer.
        workers_raw = data.get("workers_needed")
        if workers_raw in (None, ""):
            workers_needed = 1
        else:
            try:
                workers_needed = int(str(workers_raw).strip())
            except (TypeError, ValueError):
                workers_needed = 0
            if workers_needed < 1:
                return Response(
                    {"workers_needed": "Must be a positive integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Structured address parts from the mobile picker. `address` stays the
        # field web templates render, so derive it from street + house when the
        # client doesn't send one of its own.
        district = (str(data.get("district") or "")).strip()
        street = (str(data.get("street") or "")).strip()
        house = (str(data.get("house") or "")).strip()
        landmark = (str(data.get("landmark") or "")).strip()
        address = (str(data.get("address") or "")).strip()
        if not address:
            address = ", ".join(p for p in (street, house) if p)

        job = Job.objects.create(
            employer=request.user,
            title=title,
            profession_id=profession_id,
            region=region,
            job_type=job_type,
            pay_currency=pay_currency,
            pay_min=pay_min,
            pay_max=pay_max,
            pay_text=(str(data.get("pay_text") or "")).strip(),
            description=(str(data.get("description") or "")).strip(),
            contact_phone=(str(data.get("contact_phone") or "")).strip(),
            lat=self._to_float(data.get("lat")),
            lng=self._to_float(data.get("lng")),
            address=address,
            district=district,
            street=street,
            house=house,
            landmark=landmark,
            workers_needed=workers_needed,
            # Up to 4 photos, each optional individually (the app requires >=1).
            photo1=request.FILES.get("photo1"),
            photo2=request.FILES.get("photo2"),
            photo3=request.FILES.get("photo3"),
            photo4=request.FILES.get("photo4"),
            is_active=True,
        )

        serializer = JobDetailSerializer(job, context={"request": request})
        data = dict(serializer.data)
        # Non-blocking nudge: the job IS created (201). If the amount looks
        # implausible for the period, surface a warning the client can show —
        # never a 400, so legitimate edge cases still go through.
        warning = pay_period_warning(pay_min, pay_max, job_type, pay_currency)
        if warning:
            data["warnings"] = [warning]
        return Response(data, status=status.HTTP_201_CREATED)


class EmployerJobSerializer(JobListSerializer):
    """Consumer job shape + employer-only fields (is_active, applicant_count)."""
    applicant_count = serializers.IntegerField(read_only=True)

    class Meta(JobListSerializer.Meta):
        fields = JobListSerializer.Meta.fields + ["is_active", "applicant_count"]


class MyJobsAPIView(generics.ListAPIView):
    """Jobs the current user posted, newest first, with applicant counts."""
    serializer_class = EmployerJobSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return (
            Job.objects.filter(employer=self.request.user)
            .select_related("profession")
            .annotate(applicant_count=Count("applications"))
            .order_by("-created_at")
        )


class MyApplicationSerializer(serializers.ModelSerializer):
    # Reuse the consumer job shape (id, title, region, job_type, pay, profession, ...).
    job = JobListSerializer(read_only=True)
    applied_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = JobApplication
        fields = ["id", "status", "applied_at", "job"]


class MyApplicationsAPIView(generics.ListAPIView):
    """Jobs the current user has applied to, newest first."""
    serializer_class = MyApplicationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = (
            JobApplication.objects.filter(worker=self.request.user)
            .select_related("job", "job__profession")
            .order_by("-created_at")
        )
        blocked = blocked_user_ids(self.request.user)
        return qs.exclude(job__employer_id__in=blocked) if blocked else qs


# ---- employer: applicants (mobile 4d-5 / 9c) -------------------------------

# Application status -> the three strings the app understands. The model already
# stores these values; the map guards against anything else ever landing in
# the column.
_APP_STATUS = {
    JobApplication.Status.PENDING: "pending",
    JobApplication.Status.ACCEPTED: "accepted",
    JobApplication.Status.REJECTED: "rejected",
}


def _worker_stats(worker_ids):
    """{worker_id: {"jobs_done": int, "rating": float|None}} from Orders — one
    query for the whole applicant list. Ratings are the employer's 1-5 score of
    the worker (Order.employer_rating); jobs_done counts completed orders."""
    if not worker_ids:
        return {}
    rows = (
        Order.objects.filter(worker_id__in=worker_ids)
        .values("worker_id")
        .annotate(
            jobs_done=Count("id", filter=Q(status=Order.Status.COMPLETED)),
            rating=Avg("employer_rating"),
        )
    )
    return {r["worker_id"]: r for r in rows}


class EmployerApplicationSerializer(serializers.ModelSerializer):
    """One applicant as the employer app renders it. Context: `job` (for the
    distance) and `worker_stats` from _worker_stats()."""
    status = serializers.SerializerMethodField()
    worker = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = ["id", "status", "created_at", "worker"]

    def get_status(self, obj):
        return _APP_STATUS.get(obj.status, "pending")

    def get_worker(self, obj):
        job = self.context.get("job") or obj.job
        stats = (self.context.get("worker_stats") or {}).get(obj.worker_id) or {}
        user = obj.worker
        wp = getattr(user, "worker_profile", None)
        profession = getattr(wp, "profession", None)
        distance = haversine_km(
            job.lat, job.lng, getattr(wp, "lat", None), getattr(wp, "lng", None)
        )
        rating = stats.get("rating")
        return {
            "id": user.id,
            "first_name": getattr(wp, "first_name", "") or "",
            "last_name": getattr(wp, "last_name", "") or "",
            "phone": user.phone,
            "professions": [profession.name] if profession else [],
            "rating": round(float(rating), 1) if rating is not None else None,
            "jobs_done": int(stats.get("jobs_done") or 0),
            "age": getattr(wp, "age", None),
            "distance_km": round(distance, 1) if distance is not None else None,
        }


_APPLICATION_RELATED = (
    "job", "worker", "worker__worker_profile", "worker__worker_profile__profession",
)


def _serialize_applications(applications, job, request):
    stats = _worker_stats({a.worker_id for a in applications})
    return EmployerApplicationSerializer(
        applications,
        many=True,
        context={"request": request, "job": job, "worker_stats": stats},
    ).data


class JobApplicationsAPIView(APIView):
    """GET /api/jobs/<pk>/applications/ — the owner's applicant list, newest first.
    403 for anyone who is not the job's employer."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        if job.employer_id != request.user.id:
            return Response(
                {"detail": "Only the job's employer can view its applications."},
                status=status.HTTP_403_FORBIDDEN,
            )
        applications_qs = JobApplication.objects.filter(job=job)
        blocked = blocked_user_ids(request.user)
        if blocked:
            applications_qs = applications_qs.exclude(worker_id__in=blocked)
        applications = list(
            applications_qs
            .select_related(*_APPLICATION_RELATED)
            .order_by("-created_at", "-id")
        )
        return Response(_serialize_applications(applications, job, request))


class ApplicationDecisionAPIView(APIView):
    """POST /api/applications/<pk>/accept/ | /reject/ — owner only; 409 unless
    the application is still pending. Returns the updated application in the
    list shape."""
    permission_classes = [IsAuthenticated]
    new_status = None  # set by the subclasses

    def post(self, request, pk):
        application = get_object_or_404(
            JobApplication.objects.select_related(*_APPLICATION_RELATED), pk=pk
        )
        if application.job.employer_id != request.user.id:
            return Response(
                {"detail": "Only the job's employer can decide on this application."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if application.status != JobApplication.Status.PENDING:
            return Response(
                {
                    "detail": "Application is not pending.",
                    "status": _APP_STATUS.get(application.status, "pending"),
                },
                status=status.HTTP_409_CONFLICT,
            )
        application.status = self.new_status
        application.save(update_fields=["status"])
        return Response(
            _serialize_applications([application], application.job, request)[0]
        )


class ApplicationAcceptAPIView(ApplicationDecisionAPIView):
    new_status = JobApplication.Status.ACCEPTED


class ApplicationRejectAPIView(ApplicationDecisionAPIView):
    new_status = JobApplication.Status.REJECTED


class ProfessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profession
        fields = ["id", "name", "name_ru", "name_en"]


class ProfessionListAPIView(generics.ListAPIView):
    serializer_class = ProfessionSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Profession.objects.all().order_by("id")
