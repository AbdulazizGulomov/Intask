# apps/jobs/api.py
from rest_framework import serializers, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
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
            "cover", "lat", "lng", "created_at", "contact_visible",
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


class ProfessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profession
        fields = ["id", "name", "name_ru", "name_en"]


class ProfessionListAPIView(generics.ListAPIView):
    serializer_class = ProfessionSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Profession.objects.all().order_by("id")
