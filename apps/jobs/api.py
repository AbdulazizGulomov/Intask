# apps/jobs/api.py
from rest_framework import serializers, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from apps.jobs.models import Job, JobApplication


class JobListSerializer(serializers.ModelSerializer):
    cover = serializers.SerializerMethodField()
    pay = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id", "title", "region", "job_type",
            "pay_currency", "pay_min", "pay_max", "pay_text", "pay",
            "cover", "created_at",
        ]

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
        fields = JobListSerializer.Meta.fields + [
            "description", "contact_phone", "lat", "lng", "photos",
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
        qs = Job.objects.filter(is_active=True).order_by("-created_at")
        region = self.request.query_params.get("region")
        job_type = self.request.query_params.get("job_type")
        search = self.request.query_params.get("search")
        if region:
            qs = qs.filter(region=region)
        if job_type:
            qs = qs.filter(job_type=job_type)
        if search:
            qs = qs.filter(title__icontains=search)
        return qs


class JobDetailAPIView(generics.RetrieveAPIView):
    serializer_class = JobDetailSerializer
    permission_classes = [AllowAny]
    queryset = Job.objects.filter(is_active=True)


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
