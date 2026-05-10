# apps/jobs/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import Profession, Job, JobApplication


@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "jobs_count", "workers_count")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)

    @admin.display(description=_("Jobs"))
    def jobs_count(self, obj):
        return obj.jobs.count()

    @admin.display(description=_("Workers"))
    def workers_count(self, obj):
        return obj.worker_profiles.count()


class JobApplicationInline(admin.TabularInline):
    """Show applications directly on Job edit page."""
    model = JobApplication
    extra = 0
    readonly_fields = ("worker", "employer", "status", "created_at")
    can_delete = False
    verbose_name = _("Application")
    verbose_name_plural = _("Applications")
    fk_name = "job"


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_per_page = 25

    list_display = (
        "id",
        "title",
        "profession",
        "region",
        "job_type",
        "pay_display",
        "is_active_badge",
        "applications_count",
        "created_at",
    )
    list_display_links = ("id", "title")
    list_filter = ("is_active", "job_type", "profession", "region", "created_at")
    search_fields = ("title", "region", "description", "contact_phone")
    ordering = ("-created_at",)
    autocomplete_fields = ("employer", "profession")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (_("Basic info"), {
            "fields": ("title", "employer", "profession", "description"),
        }),
        (_("Location"), {
            "fields": ("region", "lat", "lng"),
        }),
        (_("Pay & type"), {
            "fields": ("job_type", "pay_currency", "pay_min", "pay_max", "pay_text"),
        }),
        (_("Photos"), {
            "fields": ("photo1", "photo2", "photo3", "photo4"),
            "classes": ("collapse",),
        }),
        (_("Contact"), {
            "fields": ("contact_phone",),
        }),
        (_("Status"), {
            "fields": ("is_active",),
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    inlines = [JobApplicationInline]

    @admin.display(description=_("Pay"))
    def pay_display(self, obj):
        if obj.pay_min and obj.pay_max:
            return f"{obj.pay_min:,.0f}–{obj.pay_max:,.0f} {obj.pay_currency}"
        if obj.pay_min:
            return f"{obj.pay_min:,.0f}+ {obj.pay_currency}"
        if obj.pay_text:
            return obj.pay_text
        return "—"

    @admin.display(description=_("Active"), ordering="is_active")
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background:#2A8A8A;color:white;padding:3px 10px;'
                'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
                _("Active"),
            )
        return format_html(
            '<span style="background:#999;color:white;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            _("Inactive"),
        )

    @admin.display(description=_("Applications"))
    def applications_count(self, obj):
        return obj.applications.count()


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_per_page = 25

    list_display = (
        "id",
        "job",
        "worker",
        "employer",
        "status_badge",
        "created_at",
    )
    list_display_links = ("id", "job")
    list_filter = ("status", "created_at")
    search_fields = (
        "job__title",
        "worker__phone",
        "worker__username",
        "employer__phone",
        "employer__username",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("job", "worker", "employer")
    readonly_fields = ("created_at",)

    @admin.display(description=_("Status"), ordering="status")
    def status_badge(self, obj):
        colors = {
            "pending": "#C9A961",
            "accepted": "#2A8A8A",
            "rejected": "#999",
        }
        color = colors.get(obj.status, "#666")
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color,
            obj.get_status_display(),
        )