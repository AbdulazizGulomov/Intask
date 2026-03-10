# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, WorkerProfile

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # --- THE FIX: Make created_at read-only so the admin page doesn't crash ---
    readonly_fields = ("created_at", "last_login")
    # --------------------------------------------------------------------------

    list_display = ("id", "phone", "username", "role", "is_active", "is_staff")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("phone", "username")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("phone", "username", "password", "role")}),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Dates", {"fields": ("last_login", "created_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "username", "password1", "password2", "role"),
        }),
    )


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "first_name",
        "last_name",
        "age",
        "gender",
        "is_completed",
        "created_at",
    )

    list_filter = (
        "gender",
        "is_completed",
        "created_at",
    )

    search_fields = (
        "first_name",
        "last_name",
        "full_name",
        "user__phone",
        "user__username",
    )

    ordering = ("-created_at",)
