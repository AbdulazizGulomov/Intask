# apps/accounts/dashboard/api_views.py
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .permissions import IsOperatorOrAdmin
from .serializers import OperatorLoginSerializer, OperatorMeSerializer


class OperatorLoginView(APIView):
    """
    POST /api/dashboard/auth/login/

    Body:
        {"phone": "+998901234567", "password": "secret123"}

    Returns on success:
        {
            "access": "<jwt>",
            "refresh": "<jwt>",
            "user": {"id": 1, "phone": "...", "role": "operator", ...}
        }
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # Login endpoint shouldn't require auth

    def post(self, request, *args, **kwargs):
        serializer = OperatorLoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Issue JWT pair
        refresh = RefreshToken.for_user(user)

        # Embed role inside the token claims so the frontend can read it without a /me/ call
        refresh["role"] = getattr(user, "role", None)
        refresh["phone"] = getattr(user, "phone", None)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": OperatorMeSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class OperatorLogoutView(APIView):
    """
    POST /api/dashboard/auth/logout/

    Body:
        {"refresh": "<jwt>"}

    Blacklists the refresh token so it can't be used again.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except TokenError:
            # Token already invalid/expired — treat as logged out anyway
            pass

        return Response(status=status.HTTP_205_RESET_CONTENT)


class OperatorMeView(APIView):
    """
    GET /api/dashboard/auth/me/

    Returns the currently authenticated operator/admin's profile.
    The React app calls this on page load to verify the JWT is still valid.
    """
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]

    def get(self, request, *args, **kwargs):
        return Response(OperatorMeSerializer(request.user).data)
    # =====================================================
    # Dashboard data endpoints (stats + charts)
    # =====================================================


from datetime import timedelta
from django.db.models import Count, Sum, Q
from django.utils import timezone

from apps.orders.models import Order
from apps.jobs.models import Profession


class DashboardStatsView(APIView):
    """
    GET /api/dashboard/stats/

    Returns 4 KPI numbers for the top-of-dashboard cards.
    """
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        prev_week_start = week_start - timedelta(days=7)

        # Active orders = scheduled or in progress, right now
        active = Order.objects.filter(
            status__in=[Order.Status.SCHEDULED, Order.Status.IN_PROGRESS]
        ).count()

        active_today = Order.objects.filter(
            status__in=[Order.Status.SCHEDULED, Order.Status.IN_PROGRESS],
            created_at__gte=today_start,
        ).count()

        # Completed this week
        completed_week = Order.objects.filter(
            status=Order.Status.COMPLETED,
            completed_at__gte=week_start,
        ).count()

        # Revenue last 7 days (completed orders)
        revenue_week_result = Order.objects.filter(
            status=Order.Status.COMPLETED,
            completed_at__gte=week_start,
        ).aggregate(total=Sum("agreed_price"))
        revenue_week = revenue_week_result["total"] or 0

        # Previous 7 days revenue (for comparison)
        revenue_prev_result = Order.objects.filter(
            status=Order.Status.COMPLETED,
            completed_at__gte=prev_week_start,
            completed_at__lt=week_start,
        ).aggregate(total=Sum("agreed_price"))
        revenue_prev = revenue_prev_result["total"] or 0

        # % change vs previous week
        if revenue_prev > 0:
            revenue_change_pct = round(
                float((revenue_week - revenue_prev) / revenue_prev * 100), 1
            )
        else:
            revenue_change_pct = None

        # Disputes pending review
        disputes = Order.objects.filter(status=Order.Status.DISPUTED).count()

        return Response({
            "active_orders": active,
            "active_orders_today": active_today,
            "completed_week": completed_week,
            "revenue_week": float(revenue_week),
            "revenue_change_pct": revenue_change_pct,
            "disputes": disputes,
        })


class OrdersTrendChartView(APIView):
    """
    GET /api/dashboard/charts/orders-trend/

    Line chart data: orders created and completed per day, last 7 days.
    """
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]

    def get(self, request):
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        labels = []
        created_data = []
        completed_data = []

        # Build 7 days going backwards
        for i in range(6, -1, -1):
            day_start = today - timedelta(days=i)
            day_end = day_start + timedelta(days=1)

            labels.append(day_start.strftime("%a"))  # Mon, Tue, ...

            created_count = Order.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end,
            ).count()

            completed_count = Order.objects.filter(
                status=Order.Status.COMPLETED,
                completed_at__gte=day_start,
                completed_at__lt=day_end,
            ).count()

            created_data.append(created_count)
            completed_data.append(completed_count)

        return Response({
            "labels": labels,
            "datasets": [
                {"label": "Created", "data": created_data},
                {"label": "Completed", "data": completed_data},
            ],
        })


class StatusMixChartView(APIView):
    """
    GET /api/dashboard/charts/status-mix/

    Donut chart data: order count per status.
    """
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]

    def get(self, request):
        # Count orders grouped by status
        rows = (
            Order.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )

        # Map raw status to display label
        status_labels = dict(Order.Status.choices)

        labels = []
        data = []
        for row in rows:
            labels.append(status_labels.get(row["status"], row["status"]))
            data.append(row["count"])

        return Response({"labels": labels, "data": data})


class TopProfessionsChartView(APIView):
    """
    GET /api/dashboard/charts/top-professions/

    Horizontal bar chart: top 6 professions by order count.
    """
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]

    def get(self, request):
        from collections import Counter

        # Manual count to avoid complex joins that may fail
        orders = Order.objects.select_related("worker__worker_profile__profession").all()

        counts = Counter()
        for order in orders:
            try:
                profession_name = order.worker.worker_profile.profession.name
                if profession_name:
                    counts[profession_name] += 1
            except (AttributeError, WorkerProfile.DoesNotExist):
                continue

        # Top 6
        top = counts.most_common(6)

        labels = [name for name, _ in top]
        data = [count for _, count in top]

        return Response({"labels": labels, "data": data})


class RevenueByDistrictChartView(APIView):
    """
    GET /api/dashboard/charts/revenue-by-district/

    Bar chart: total revenue per district (extracted from address).
    """
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]

    def get(self, request):
        # Aggregate completed orders by district name
        # We use the first word of the address as district name
        # (since seed data uses "<District> district, Tashkent" format)
        completed = Order.objects.filter(
            status=Order.Status.COMPLETED,
            agreed_price__isnull=False,
        )

        # Group by district (first word of address)
        district_totals = {}
        for order in completed:
            address = (order.address or "").strip()
            if not address:
                continue
            district = address.split()[0]  # "Yunusobod district..." → "Yunusobod"
            district_totals[district] = district_totals.get(district, 0) + float(order.agreed_price)

        # Sort by revenue, top 6
        sorted_districts = sorted(district_totals.items(), key=lambda x: x[1], reverse=True)[:6]

        labels = [d[0] for d in sorted_districts]
        # Convert to millions (e.g. 14_200_000 → 14.2)
        data = [round(d[1] / 1_000_000, 2) for d in sorted_districts]

        return Response({
            "labels": labels,
            "data": data,
            "unit": "M UZS",
        })

# =====================================================
# CRUD ViewSets (Orders + Masters)
# =====================================================
from rest_framework import viewsets, mixins, filters
from rest_framework.pagination import PageNumberPagination

from apps.accounts.models import WorkerProfile
from .serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    OrderUpdateSerializer,
    MasterListSerializer,
)


class DashboardPagination(PageNumberPagination):
    """Standard pagination: 25 per page, max 100."""
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Orders ViewSet — list, retrieve, partial_update.
    No 'create' (orders come from job applications).
    No 'destroy' (operators can't delete orders, only cancel them).
    """
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]
    pagination_class = DashboardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "title",
        "description",
        "address",
        "employer__phone",
        "worker__phone",
    ]
    ordering_fields = ["created_at", "scheduled_at", "agreed_price", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Order.objects.select_related("employer", "worker").prefetch_related("status_history")

        # Filter by status (e.g. ?status=scheduled,in_progress)
        status_param = self.request.query_params.get("status")
        if status_param:
            statuses = [s.strip() for s in status_param.split(",") if s.strip()]
            qs = qs.filter(status__in=statuses)

        # Filter by date range (?from=2026-05-01&to=2026-05-10)
        date_from = self.request.query_params.get("from")
        date_to = self.request.query_params.get("to")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        if self.action in ("update", "partial_update"):
            return OrderUpdateSerializer
        return OrderDetailSerializer

    def update(self, request, *args, **kwargs):
        # Always do partial updates (PATCH-style) so operators don't need to send all fields
        kwargs["partial"] = True
        response = super().update(request, *args, **kwargs)
        # After update, return the full detail (not the slim update serializer)
        instance = self.get_object()
        return Response(OrderDetailSerializer(instance, context={"request": request}).data)


class MasterViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Masters ViewSet — read-only listing of worker profiles.
    Operators see workers; managing them happens elsewhere.
    """
    permission_classes = [IsAuthenticated, IsOperatorOrAdmin]
    pagination_class = DashboardPagination
    serializer_class = MasterListSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "first_name",
        "last_name",
        "full_name",
        "user__phone",
        "profession__name",
    ]
    ordering_fields = ["created_at", "age"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = WorkerProfile.objects.select_related("user", "profession")

        # Filter by profession id
        profession_id = self.request.query_params.get("profession")
        if profession_id:
            qs = qs.filter(profession_id=profession_id)

        # Filter by completed/incomplete profile
        is_completed = self.request.query_params.get("is_completed")
        if is_completed in ("true", "1"):
            qs = qs.filter(is_completed=True)
        elif is_completed in ("false", "0"):
            qs = qs.filter(is_completed=False)

        # Filter by active user
        is_active = self.request.query_params.get("is_active")
        if is_active in ("true", "1"):
            qs = qs.filter(user__is_active=True)
        elif is_active in ("false", "0"):
            qs = qs.filter(user__is_active=False)

        return qs