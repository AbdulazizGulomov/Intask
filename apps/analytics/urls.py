# apps/analytics/urls.py
from django.urls import path

from .api_views import (
    AnalyticsKpisView,
    AnalyticsFunnelView,
    AnalyticsClientsTrendView,
    AnalyticsSupplyDemandView,
)

urlpatterns = [
    path("kpis/", AnalyticsKpisView.as_view(), name="analytics_kpis"),
    path("funnel/", AnalyticsFunnelView.as_view(), name="analytics_funnel"),
    path("clients-trend/", AnalyticsClientsTrendView.as_view(), name="analytics_clients_trend"),
    path("supply-demand/", AnalyticsSupplyDemandView.as_view(), name="analytics_supply_demand"),
]
