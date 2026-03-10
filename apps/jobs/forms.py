# apps/jobs/forms.py

from django import forms
from .models import Job


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            "title",

            # 4 PHOTOS
            "photo1",
            "photo2",
            "photo3",
            "photo4",

            "region",
            "job_type",

            "pay_currency",
            "pay_min",
            "pay_max",
            "pay_text",

            "description",
            "contact_phone",

            "lat",
            "lng",
        ]

        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }
