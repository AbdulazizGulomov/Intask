# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import User, WorkerProfile


class WorkerProfileInline(admin.StackedInline):
    """Show worker profile directly on User edit page."""
    model = WorkerProfile
    can_delete = False
    verbose_name = _("Worker Profile")
    verbose_name_plural = _("Worker Profile")
    fk_name = "user"
    extra = 0
    readonly_fields = ("full_name", "created_at", "updated_at")
    fieldsets = (
        (_("Personal info"), {
            "fields": ("first_name", "last_name", "full_name", "age", "gender", "photo"),
        }),
        (_("Professional"), {
            "fields": ("profession", "certificate", "is_completed"),
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    readonly_fields = ("created_at", "last_login")
    list_per_page = 25

    list_display = (
        "id",
        "phone",
        "username",
        "role_badge",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_display_links = ("id", "phone", "username")
    list_filter = ("role", "is_staff", "is_active", "created_at")
    search_fields = ("phone", "username")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("phone", "username", "password", "role")}),
        (_("Permissions"), {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
            "classes": ("collapse",),
        }),
        (_("Dates"), {
            "fields": ("last_login", "created_at"),
            "classes": ("collapse",),
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "username", "password1", "password2", "role"),
        }),
    )

    inlines = [WorkerProfileInline]

    @admin.display(description=_("Role"), ordering="role")
    def role_badge(self, obj):
        colors = {
            "worker": "#2A8A8A",
            "employer": "#1A2B4A",
            "admin": "#C9A961",
        }
        color = colors.get(obj.role, "#666")
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color,
            obj.get_role_display(),
        )

    def get_inline_instances(self, request, obj=None):
        """Only show WorkerProfile inline for worker role."""
        if obj and obj.role == User.Role.WORKER:
            return super().get_inline_instances(request, obj)
        return []


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_per_page = 25

    list_display = (
        "id",
        "photo_thumb",
        "full_name",
        "user_phone",
        "profession",
        "age",
        "gender",
        "is_completed",
        "created_at",
    )
    list_display_links = ("id", "full_name")
    list_filter = ("gender", "is_completed", "profession", "created_at")
    search_fields = (
        "first_name",
        "last_name",
        "full_name",
        "user__phone",
        "user__username",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("user", "profession")
    readonly_fields = ("full_name", "created_at", "updated_at")

    fieldsets = (
        (_("Account"), {
            "fields": ("user",),
        }),
        (_("Personal info"), {
            "fields": ("first_name", "last_name", "full_name", "age", "gender", "photo"),
        }),
        (_("Professional"), {
            "fields": ("profession", "certificate", "is_completed"),
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description=_("Photo"))
    def photo_thumb(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width:36px;height:36px;border-radius:50%;'
                'object-fit:cover;" />',
                obj.photo.url,
            )
        return "—"

    @admin.display(description=_("Phone"), ordering="user__phone")
    def user_phone(self, obj):
        return obj.user.phone or obj.user.username or "—"