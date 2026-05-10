# apps/orders/management/commands/seed_dashboard.py
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User, WorkerProfile
from apps.jobs.models import Profession, Job
from apps.orders.models import Order, OrderStatusHistory


PROFESSIONS = [
    "Mebel ustasi", "Bo'yoqchi", "Bog'bon", "Usta",
    "Kompyuter ustasi", "Telefon ustasi", "Deraza ustasi", "Qulflash ustasi",
]

DISTRICTS = [
    ("toshkent_city", "Yunusobod"),
    ("toshkent_city", "Chilonzor"),
    ("toshkent_city", "Mirobod"),
    ("toshkent_city", "Sergeli"),
    ("toshkent_city", "Yakkasaroy"),
    ("toshkent_city", "Olmazor"),
]

EMPLOYER_PHONES = [
    "+998901111101", "+998901111102", "+998901111103",
    "+998901111104", "+998901111105",
]

WORKER_PHONES = [
    "+998902222201", "+998902222202", "+998902222203", "+998902222204",
    "+998902222205", "+998902222206", "+998902222207", "+998902222208",
]


class Command(BaseCommand):
    help = "Seed the database with fake employers, workers, and 50 orders for dashboard testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--orders",
            type=int,
            default=50,
            help="Number of orders to create (default: 50)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete existing seed data before creating new",
        )

    def handle(self, *args, **options):
        n_orders = options["orders"]
        clean = options["clean"]

        if clean:
            self.stdout.write(self.style.WARNING("Cleaning existing seed data..."))
            Order.objects.filter(title__startswith="[SEED]").delete()
            User.objects.filter(phone__in=EMPLOYER_PHONES + WORKER_PHONES).delete()

        self.stdout.write(self.style.SUCCESS("Creating professions..."))
        professions = []
        for name in PROFESSIONS:
            p, _ = Profession.objects.get_or_create(name=name)
            professions.append(p)

        self.stdout.write(self.style.SUCCESS("Creating employers..."))
        employers = []
        for phone in EMPLOYER_PHONES:
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={"role": User.Role.EMPLOYER, "is_active": True},
            )
            if created:
                user.set_unusable_password()
                user.save()
            employers.append(user)

        self.stdout.write(self.style.SUCCESS("Creating workers..."))
        workers = []
        for i, phone in enumerate(WORKER_PHONES):
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={"role": User.Role.WORKER, "is_active": True},
            )
            if created:
                user.set_unusable_password()
                user.save()
            # Worker profile
            profile, _ = WorkerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "first_name": f"Worker{i+1}",
                    "last_name": "Test",
                    "age": 25 + i,
                    "gender": "male" if i % 2 == 0 else "female",
                    "profession": random.choice(professions),
                    "is_completed": True,
                },
            )
            workers.append(user)

        self.stdout.write(self.style.SUCCESS(f"Creating {n_orders} orders..."))

        statuses = [
            (Order.Status.SCHEDULED, 0.20),
            (Order.Status.IN_PROGRESS, 0.20),
            (Order.Status.COMPLETED, 0.45),
            (Order.Status.CANCELLED, 0.10),
            (Order.Status.DISPUTED, 0.05),
        ]

        now = timezone.now()
        created_count = 0

        for i in range(n_orders):
            employer = random.choice(employers)
            worker = random.choice(workers)
            profession = random.choice(professions)
            region_key, district_name = random.choice(DISTRICTS)

            # Status weighted
            r = random.random()
            cumulative = 0
            status = Order.Status.SCHEDULED
            for s, weight in statuses:
                cumulative += weight
                if r <= cumulative:
                    status = s
                    break

            # Spread creation dates over the last 14 days
            days_ago = random.randint(0, 13)
            hours_ago = random.randint(0, 23)
            created_at = now - timedelta(days=days_ago, hours=hours_ago)

            # Price between 100k and 1.5M UZS
            price = Decimal(random.randint(100, 1500) * 1000)

            scheduled_at = created_at + timedelta(days=random.randint(1, 5))
            started_at = None
            completed_at = None

            if status in (Order.Status.IN_PROGRESS, Order.Status.COMPLETED):
                started_at = scheduled_at + timedelta(hours=random.randint(0, 6))
            if status == Order.Status.COMPLETED:
                completed_at = started_at + timedelta(hours=random.randint(1, 8))

            order = Order.objects.create(
                employer=employer,
                worker=worker,
                title=f"[SEED] {profession.name} — {district_name}",
                description=f"Auto-generated order for testing. District: {district_name}.",
                agreed_price=price,
                currency="UZS",
                scheduled_at=scheduled_at,
                started_at=started_at,
                completed_at=completed_at,
                address=f"{district_name} district, Tashkent",
                status=status,
            )

            # Backdate created_at (Django sets auto_now_add, so we override with .update())
            Order.objects.filter(pk=order.pk).update(created_at=created_at)

            # Add a status history entry for non-scheduled
            if status != Order.Status.SCHEDULED:
                OrderStatusHistory.objects.create(
                    order=order,
                    from_status=Order.Status.SCHEDULED,
                    to_status=status,
                    note=f"Auto-transitioned to {status} by seed script",
                )

            # Ratings for completed orders
            if status == Order.Status.COMPLETED:
                order.employer_rating = random.randint(3, 5)
                order.worker_rating = random.randint(3, 5)
                order.save(update_fields=["employer_rating", "worker_rating"])

            created_count += 1

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS(f"  Seed complete!"))
        self.stdout.write(self.style.SUCCESS(f"  Employers: {len(employers)}"))
        self.stdout.write(self.style.SUCCESS(f"  Workers:   {len(workers)}"))
        self.stdout.write(self.style.SUCCESS(f"  Orders:    {created_count}"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write("Run 'python manage.py runserver' and visit /admin/ to see the data.")