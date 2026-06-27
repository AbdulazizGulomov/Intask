# apps/jobs/forms.py

from django import forms
from django.utils.translation import get_language

from .models import Job


class JobForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show each profession option in the active language (fallback: Uzbek).
        if "profession" in self.fields:
            lang = get_language()
            self.fields["profession"].label_from_instance = (
                lambda obj: obj.display_name(lang)
            )

    class Meta:
        model = Job
        fields = [
            "title",

            "profession",

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
