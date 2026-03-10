from django.core.management.base import BaseCommand
from apps.jobs.models import Profession

PROFESSIONS = [
    "Yordamchi ishchi",
    "Quruvchi",
    "Santexnik",
    "Elektrik",
    "Payvandchi",
    "Haydovchi",
    "Yuk tashuvchi",
    "Kuryer",
    "Oshpaz",
    "Kichkintoylar qarovchisi",
    "Tozalovchi",
    "Bog'bon",
    "Usta",
    "Konditsioner ustasi",
    "Kompyuter ustasi",
    "Telefon ustasi",
    "Deraza ustasi",
    "Mebel ustasi",
    "Bo'yoqchi",
    "Qulflash ustasi",
]

class Command(BaseCommand):
    help = "Seed default professions"

    def handle(self, *args, **options):
        created_count = 0

        for name in PROFESSIONS:
            _, created = Profession.objects.get_or_create(name=name)
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created_count} new professions."
            )
        )