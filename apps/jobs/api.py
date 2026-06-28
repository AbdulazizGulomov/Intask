# apps/jobs/api.py
from decimal import Decimal, InvalidOperation

from rest_framework import serializers, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count
from django.shortcuts import get_object_or_404
from apps.jobs.models import Job, JobApplication, Profession


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
            "cover", "lat", "lng", "created_at",
            "contact_phone", "contact_visible",
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
        if obj.pay_min and obj.pay_max:
            return f"{obj.pay_min:,.0f}–{obj.pay_max:,.0f} {obj.pay_currency}"
        if obj.pay_min:
            return f"{obj.pay_min:,.0f} {obj.pay_currency}"
        return obj.pay_text or ""


class JobDetailSerializer(JobListSerializer):
    photos = serializers.SerializerMethodField()

    class Meta(JobListSerializer.Meta):
        # lat/lng now come from JobListSerializer.Meta.fields (added for the list);
        # only the detail-only fields are appended here.
        fields = JobListSerializer.Meta.fields + [
            "description", "contact_phone", "photos",
        ]

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
        return qs


class JobDetailAPIView(generics.RetrieveAPIView):
    serializer_class = JobDetailSerializer
    permission_classes = [AllowAny]
    queryset = Job.objects.filter(is_active=True).select_related("profession")


class JobApplyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, is_active=True)
        user = request.user
        if getattr(user, "role", None) and user.role != "worker":
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
            photo1=request.FILES.get("photo1"),
            is_active=True,
        )

        serializer = JobDetailSerializer(job, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
        return (
            JobApplication.objects.filter(worker=self.request.user)
            .select_related("job", "job__profession")
            .order_by("-created_at")
        )


class ProfessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profession
        fields = ["id", "name", "name_ru", "name_en"]


class ProfessionListAPIView(generics.ListAPIView):
    serializer_class = ProfessionSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Profession.objects.all().order_by("id")
