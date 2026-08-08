"""Seed the Google Play reviewer account plus a few visible demo jobs.

Pairs with settings.PLAY_REVIEW_PHONE / PLAY_REVIEW_OTP (server .env only) and
the reviewer branch in apps/accounts/auth/otp.py. Unlike seed_test_users this
IS allowed in production — that is where the Play review happens.

Creates idempotently:
  * the reviewer user (role=worker, never staff) with a COMPLETE worker
    profile, so login lands on /worker/ instead of the register form;
  * one demo employer (reserved-fake number +998900000004) with three active
    jobs carrying Tashkent coordinates, so the reviewer does not see an empty
    map/list.

The reviewer phone is masked in output and the OTP code is never printed.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.auth.otp import normalize_phone
from apps.accounts.models import User, WorkerProfile
from apps.jobs.models import Job, Profession

DEMO_EMPLOYER_PHONE = "+998900000004"

DEMO_JOBS = [
    {
        "title": "Elektrik kerak — rozetka va lyustra o'rnatish",
        "profession": "Elektrik",
        "job_type": Job.JobType.HOURLY,
        "pay_min": 80000, "pay_max": 120000,
        "description": "2 xonali kvartirada 4 ta rozetka almashtirish va lyustra o'rnatish kerak.",
        "lat": 41.3111, "lng": 69.2797, "address": "Toshkent, Amir Temur ko'chasi",
    },
    {
        "title": "Santexnik — kran va sifon almashtirish",
        "profession": "Santexnik",
        "job_type": Job.JobType.HOURLY,
        "pay_min": 100000, "pay_max": 150000,
        "description": "Oshxonada kran oqmoqda, sifonni ham almashtirish kerak.",
        "lat": 41.2995, "lng": 69.2401, "address": "Toshkent, Chilonzor tumani",
    },
    {
        "title": "Uy tozalash — 3 xonali kvartira",
        "profession": "Tozalash",
        "job_type": Job.JobType.DAILY,
        "pay_min": 200000, "pay_max": 300000,
        "description": "3 xonali kvartirani to'liq tozalash (derazalar bilan).",
        "lat": 41.3265, "lng": 69.2285, "address": "Toshkent, Yunusobod tumani",
    },
]


def _mask(phone: str) -> str:
    """+998996177337 -> +998*****7337 — enough to recognise, never the full number."""
    return phone[:4] + "*" * max(0, len(phone) - 8) + phone[-4:] if len(phone) >= 8 else "****"


class Command(BaseCommand):
    help = (
        "Seed the Google Play reviewer worker account (from PLAY_REVIEW_PHONE) "
        "and three demo jobs. Safe to re-run; allowed in production."
    )

    def handle(self, *args, **options):
        review_phone = normalize_phone(getattr(settings, "PLAY_REVIEW_PHONE", "") or "")
        if not review_phone:
            raise CommandError(
                "PLAY_REVIEW_PHONE is not set (or invalid). Add it to the server "
                ".env before seeding."
            )
        if not (getattr(settings, "PLAY_REVIEW_OTP", "") or ""):
            self.stdout.write(self.style.WARNING(
                "PLAY_REVIEW_OTP is not set — the login bypass is disabled until "
                "it is added to the .env. Seeding data anyway."
            ))

        # ---- Reviewer: worker with a COMPLETE profile -> lands on /worker/ ----
        reviewer, created = User.objects.get_or_create(
            phone=review_phone,
            defaults={"role": User.Role.WORKER, "is_active": True},
        )
        changed = []
        if reviewer.role != User.Role.WORKER:
            reviewer.role = User.Role.WORKER
            changed.append("role")
        if not reviewer.is_active:
            reviewer.is_active = True
            changed.append("is_active")
        # verify-otp returns 403 for staff — the reviewer must never be staff.
        if reviewer.is_staff or reviewer.is_superuser:
            reviewer.is_staff = False
            reviewer.is_superuser = False
            changed.append("cleared-staff")
        if reviewer.has_usable_password():
            reviewer.set_unusable_password()
            changed.append("password")
        if changed:
            reviewer.save()

        profession, _ = Profession.objects.get_or_create(name="Elektrik")
        profile, p_created = WorkerProfile.objects.get_or_create(user=reviewer)
        profile.first_name = profile.first_name or "Google"
        profile.last_name = profile.last_name or "Reviewer"
        profile.age = profile.age or 30
        profile.gender = profile.gender or WorkerProfile.Gender.MALE
        if not profile.profession_id:
            profile.profession = profession
        profile.is_completed = True
        profile.save()

        # ---- Demo employer + three visible jobs with map coordinates ----
        employer, _ = User.objects.get_or_create(
            phone=DEMO_EMPLOYER_PHONE,
            defaults={"role": User.Role.EMPLOYER, "is_active": True},
        )
        contact = getattr(settings, "SUPPORT_PHONE", "") or ""
        jobs_created = 0
        for spec in DEMO_JOBS:
            prof, _ = Profession.objects.get_or_create(name=spec["profession"])
            _, j_created = Job.objects.get_or_create(
                employer=employer,
                title=spec["title"],
                defaults={
                    "profession": prof,
                    "region": "toshkent_city",
                    "job_type": spec["job_type"],
                    "pay_currency": Job.Currency.UZS,
                    "pay_min": spec["pay_min"],
                    "pay_max": spec["pay_max"],
                    "description": spec["description"],
                    "contact_phone": contact,
                    "lat": spec["lat"],
                    "lng": spec["lng"],
                    "address": spec["address"],
                    "is_active": True,
                },
            )
            jobs_created += int(j_created)

        self.stdout.write(self.style.SUCCESS(
            f"reviewer {_mask(review_phone)}: {'created' if created else 'updated'} "
            f"(profile {'created' if p_created else 'updated'}, is_completed=True)"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"demo employer {DEMO_EMPLOYER_PHONE}: {jobs_created} new job(s), "
            f"{len(DEMO_JOBS) - jobs_created} already present"
        ))
