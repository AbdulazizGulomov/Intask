# apps/orders/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import Order, OrderStatusHistory


BADGE_STYLE = "background:{};color:white;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:600;"


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "changed_by", "note", "created_at")
    can_delete = False
    verbose_name = _("Status change")
    verbose_name_plural = _("Status history")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_per_page = 25

    list_display = (
        "id",
        "title",
        "employer_phone",
        "worker_phone",
        "status_badge",
        "price_display",
        "scheduled_at",
        "created_at",
    )
    list_display_links = ("id", "title")
    list_filter = ("status", "currency", "created_at", "scheduled_at")
    search_fields = (
        "title",
        "description",
        "address",
        "employer__phone",
        "worker__phone",
        "employer__username",
        "worker__username",
    )
    ordering = ("-created_at",)
    autocomplete_fields = ("employer", "worker", "job", "job_application", "cancelled_by")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (_("Parties"), {"fields": ("employer", "worker")}),
        (_("Job link"), {"fields": ("job", "job_application"), "classes": ("collapse",)}),
        (_("Details"), {"fields": ("title", "description")}),
        (_("Money"), {"fields": ("agreed_price", "currency")}),
        (_("Schedule"), {"fields": ("scheduled_at", "started_at", "completed_at")}),
        (_("Location"), {"fields": ("address", "lat", "lng")}),
        (_("Status"), {"fields": ("status",)}),
        (_("Ratings & reviews"), {
            "fields": ("employer_rating", "employer_review", "worker_rating", "worker_review"),
            "classes": ("collapse",),
        }),
        (_("Cancellation"), {
            "fields": ("cancellation_reason", "cancelled_by"),
            "classes": ("collapse",),
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    inlines = [OrderStatusHistoryInline]

    @admin.display(description=_("Employer"), ordering="employer__phone")
    def employer_phone(self, obj):
        return obj.employer.phone or obj.employer.username or "—"

    @admin.display(description=_("Worker"), ordering="worker__phone")
    def worker_phone(self, obj):
        return obj.worker.phone or obj.worker.username or "—"

    @admin.display(description=_("Price"))
    def price_display(self, obj):
        if obj.agreed_price:
            return f"{obj.agreed_price:,.0f} {obj.currency}"
        return "—"

    @admin.display(description=_("Status"), ordering="status")
    def status_badge(self, obj):
        colors = {
            "scheduled": "#C9A961",
            "in_progress": "#2A8A8A",
            "completed": "#1A2B4A",
            "cancelled": "#999",
            "disputed": "#D85A30",
        }
        color = colors.get(obj.status, "#666")
        html = '<span style="' + BADGE_STYLE.format(color) + '">{}</span>'
        return format_html(html, obj.get_status_display())


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_per_page = 50

    list_display = (
        "id",
        "order",
        "from_status",
        "to_status",
        "changed_by",
        "created_at",
    )
    list_display_links = ("id", "order")
    list_filter = ("to_status", "created_at")
    search_fields = ("order__title", "note", "changed_by__phone")
    ordering = ("-created_at",)
    autocomplete_fields = ("order", "changed_by")
    readonly_fields = ("created_at",)