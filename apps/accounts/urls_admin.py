# apps/accounts/urls_admin.py
from django.urls import path
from apps.accounts import dashboard_views

urlpatterns = [
    path("", dashboard_views.admin_login, name="admin_login_root"), # Catch /admin/
    path("login/", dashboard_views.admin_login, name="admin_login"),
    path("logout/", dashboard_views.admin_logout, name="admin_logout"),
    path("dashboard/", dashboard_views.admin_dashboard, name="admin_dashboard"),
]
