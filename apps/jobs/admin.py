from django.contrib import admin
from .models import Job, Profession

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "region", "district", "job_type",
        "is_active", "created_at"
    )
    list_filter = ("region", "job_type", "is_active")
    search_fields = ("title", "region", "district", "street", "landmark")
    ordering = ("-created_at",)

@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
