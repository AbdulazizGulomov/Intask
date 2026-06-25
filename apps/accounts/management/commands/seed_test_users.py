"""Seed DEBUG-only fixed test users for the OTP login/register flow.

Pairs with settings.OTP_TEST_NUMBERS + the DEBUG-only branch in
apps/accounts/auth/otp.send_otp. Running this is safe scaffolding for local dev:

  +998900000001  → WORKER with a COMPLETE profile  → login lands on /worker/
  +998900000002  → EMPLOYER                        → login lands on /employer/
  +998900000003  → intentionally LEFT UNSEEDED     → first-time register → /role/

Refuses to run when DEBUG is False (production), so it can never create or mutate
accounts on a real deployment.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User, WorkerProfile

WORKER_PHONE = "+998900000001"
EMPLOYER_PHONE = "+998900000002"
FRESH_PHONE = "+998900000003"


class Command(BaseCommand):
    help = "Seed DEBUG-only fixed OTP test users (worker + employer). Refuses to run when DEBUG=False."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "seed_test_users only runs with DEBUG=True. Refusing in production."
            )

        # ---- 1) Returning WORKER with a COMPLETE profile -> lands on /worker/ ----
        worker, w_created = User.objects.get_or_create(
            phone=WORKER_PHONE,
            defaults={"role": User.Role.WORKER, "is_active": True},
        )
        changed = []
        if worker.role != User.Role.WORKER:
            worker.role = User.Role.WORKER
            changed.append("role")
        if not worker.is_active:
            worker.is_active = True
            changed.append("is_active")
        # OTP consumers must NOT be staff/superuser, or verify-otp blocks them (403).
        if worker.is_staff or worker.is_superuser:
            worker.is_staff = False
            worker.is_superuser = False
            changed.append("cleared-staff")
        if worker.has_usable_password():
            worker.set_unusable_password()  # OTP users never use a password
            changed.append("password")
        if changed:
            worker.save()

        # Placeholder profession (FK to jobs.Profession) — created idempotently.
        profession = None
        try:
            from apps.jobs.models import Profession
            profession, _ = Profession.objects.get_or_create(name="Elektrik")
        except Exception as exc:  # pragma: no cover - profession is optional
            self.stdout.write(self.style.WARNING(f"  (profession skipped: {exc})"))

        profile, p_created = WorkerProfile.objects.get_or_create(user=worker)
        # Fill required completeness fields with placeholders (don't clobber real data).
        profile.first_name = profile.first_name or "Test"
        profile.last_name = profile.last_name or "Worker"
        profile.age = profile.age or 30
        profile.gender = profile.gender or WorkerProfile.Gender.MALE
        if profession and not profile.profession_id:
            profile.profession = profession
        profile.is_completed = True  # so login goes to /worker/, not /worker/register/
        profile.save()

        # ---- 2) Returning EMPLOYER -> lands on /employer/ ----
        employer, e_created = User.objects.get_or_create(
            phone=EMPLOYER_PHONE,
            defaults={"role": User.Role.EMPLOYER, "is_active": True},
        )
        e_changed = []
        if employer.role != User.Role.EMPLOYER:
            employer.role = User.Role.EMPLOYER
            e_changed.append("role")
        if not employer.is_active:
            employer.is_active = True
            e_changed.append("is_active")
        if employer.is_staff or employer.is_superuser:
            employer.is_staff = False
            employer.is_superuser = False
            e_changed.append("cleared-staff")
        if employer.has_usable_password():
            employer.set_unusable_password()
            e_changed.append("password")
        if e_changed:
            employer.save()

        # ---- 3) FRESH number -> ensure NO user so it exercises first-time register ----
        removed, _ = User.objects.filter(phone=FRESH_PHONE).delete()

        # ---- Report ----
        self.stdout.write(self.style.SUCCESS(
            f"worker   {WORKER_PHONE}: {'created' if w_created else 'updated'} "
            f"(role={worker.role}, profile {'created' if p_created else 'updated'}, "
            f"is_completed={profile.is_completed}, profession={getattr(profile.profession, 'name', None)})"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"employer {EMPLOYER_PHONE}: {'created' if e_created else 'updated'} (role={employer.role})"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"fresh    {FRESH_PHONE}: left UNSEEDED "
            f"({'removed existing user' if removed else 'no user present'}) -> first-time register"
        ))
        self.stdout.write(self.style.NOTICE(
            "Login locally with code 123456 (DEBUG only, no SMS sent)."
        ))