# apps/accounts/dashboard/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .api_views import (
    # Auth
    OperatorLoginView,
    OperatorLogoutView,
    OperatorMeView,
    # Stats + Charts
    DashboardStatsView,
    OrdersTrendChartView,
    StatusMixChartView,
    TopProfessionsChartView,
    RevenueByDistrictChartView,
    # ViewSets
    OrderViewSet,
    MasterViewSet,
    ClientViewSet,
)


# Router for ViewSets (auto-creates list/detail/update routes)
router = DefaultRouter()
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"masters", MasterViewSet, basename="master")
router.register(r"clients", ClientViewSet, basename="client")


app_name = "dashboard"

urlpatterns = [
    # Auth
    path("auth/login/", OperatorLoginView.as_view(), name="login"),
    path("auth/logout/", OperatorLogoutView.as_view(), name="logout"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("auth/me/", OperatorMeView.as_view(), name="me"),

    # Stats (KPIs)
    path("stats/", DashboardStatsView.as_view(), name="stats"),

    # Charts
    path("charts/orders-trend/", OrdersTrendChartView.as_view(), name="chart_orders_trend"),
    path("charts/status-mix/", StatusMixChartView.as_view(), name="chart_status_mix"),
    path("charts/top-professions/", TopProfessionsChartView.as_view(), name="chart_top_professions"),
    path("charts/revenue-by-district/", RevenueByDistrictChartView.as_view(), name="chart_revenue_district"),

    # CRUD ViewSets (auto-generates: /orders/, /orders/<id>/, /masters/, /masters/<id>/, /clients/, /clients/<id>/)
    path("", include(router.urls)),
]