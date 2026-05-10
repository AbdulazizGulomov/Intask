# apps/accounts/dashboard/permissions.py
from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsOperator(BasePermission):
    """Only users with role='operator' can access."""

    message = "Only operators can access this resource."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and getattr(user, "role", None) == User.Role.OPERATOR
        )


class IsOperatorOrAdmin(BasePermission):
    """Operators and admins can access. Use this for most dashboard endpoints."""

    message = "Only operators or admins can access this resource."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False

        role = getattr(user, "role", None)
        return role in (User.Role.OPERATOR, User.Role.ADMIN) or user.is_superuser


class IsAdminOnly(BasePermission):
    """Admin-only actions (e.g. creating operators, financial overrides)."""

    message = "Only admins can perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False

        return getattr(user, "role", None) == User.Role.ADMIN or user.is_superuser