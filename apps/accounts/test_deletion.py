"""Account deletion tests (App Store Guideline 5.1.1(v)).

Covers the endpoint contract, that deletion is real rather than a
deactivation, that tokens stop working, that one user's deletion leaves
everyone else untouched, that media and OTP cache keys are cleaned up, and
that the same phone can register again afterwards.
"""

import io

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.auth.otp import otp_attempts_key, otp_cache_key
from apps.accounts.models import WorkerProfile
from apps.accounts.services.deletion import delete_user_account
from apps.jobs.models import Job, JobApplication
from apps.moderation.models import Block, Report
from apps.orders.models import Order

User = get_user_model()

URL = "/api/me/"


def make_user(phone, role="worker", **kwargs):
    return User.objects.create(phone=phone, role=role, **kwargs)


def make_job(employer, title="Elektrik kerak", **kwargs):
    defaults = {"region": "toshkent_city", "job_type": Job.JobType.HOURLY, "is_active": True}
    defaults.update(kwargs)
    return Job.objects.create(employer=employer, title=title, **defaults)


def tiny_png():
    """Smallest valid PNG, so ImageField validation passes."""
    return SimpleUploadedFile(
        "p.png",
        (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
            b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        ),
        content_type="image/png",
    )


def auth(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class DeleteMeEndpointTests(TestCase):
    def setUp(self):
        self.user = make_user("+998900010001")

    def test_delete_returns_204_and_removes_the_user(self):
        response = auth(self.user).delete(URL)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_unauthenticated_delete_is_401(self):
        response = APIClient().delete(URL)
        self.assertEqual(response.status_code, 401)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_staff_cannot_delete_themselves(self):
        staff = make_user("+998900010002", is_staff=True)
        response = auth(staff).delete(URL)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=staff.pk).exists())

    def test_superuser_cannot_delete_themselves(self):
        root = make_user("+998900010003", is_superuser=True)
        response = auth(root).delete(URL)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=root.pk).exists())

    def test_get_and_patch_still_work(self):
        client = auth(self.user)
        self.assertEqual(client.get(URL).status_code, 200)
        self.assertEqual(client.patch(URL, {"first_name": "Ali"}, format="json").status_code, 200)

    def test_delete_is_a_deletion_not_a_deactivation(self):
        auth(self.user).delete(URL)
        # Not merely is_active=False — the row itself is gone.
        self.assertFalse(User.objects.filter(phone="+998900010001").exists())
        self.assertEqual(User.all_objects.count() if hasattr(User, "all_objects") else User.objects.count(), 0)


class DeleteRemovesRelatedDataTests(TestCase):
    def setUp(self):
        self.user = make_user("+998900011001", role="employer")
        self.other = make_user("+998900011002", role="employer")

        WorkerProfile.objects.create(user=self.user, first_name="Ali", last_name="Valiev")
        self.job = make_job(self.user)
        self.other_job = make_job(self.other, title="Boshqa ish")

        # The user applied to someone else's job, and someone applied to theirs.
        JobApplication.objects.create(job=self.other_job, worker=self.user, employer=self.other)
        JobApplication.objects.create(job=self.job, worker=self.other, employer=self.user)

        # Moderation rows in every direction.
        Report.objects.create(reporter=self.user, target_type="user", target_user=self.other, reason="spam")
        Report.objects.create(reporter=self.other, target_type="user", target_user=self.user, reason="abuse")
        Report.objects.create(reporter=self.other, target_type="job", target_job=self.job, reason="fraud")
        Block.objects.create(blocker=self.user, blocked=self.other)
        Block.objects.create(blocker=self.other, blocked=self.user)

        # Orders on both sides - these are the PROTECT FKs.
        Order.objects.create(employer=self.user, worker=self.other, title="A")
        Order.objects.create(employer=self.other, worker=self.user, title="B")

    def test_everything_belonging_to_the_user_is_gone(self):
        self.assertEqual(auth(self.user).delete(URL).status_code, 204)

        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(WorkerProfile.objects.filter(user_id=self.user.pk).exists())
        self.assertFalse(Job.objects.filter(pk=self.job.pk).exists())
        self.assertFalse(JobApplication.objects.filter(worker_id=self.user.pk).exists())
        self.assertFalse(JobApplication.objects.filter(employer_id=self.user.pk).exists())
        self.assertFalse(Report.objects.filter(reporter_id=self.user.pk).exists())
        self.assertFalse(Report.objects.filter(target_user_id=self.user.pk).exists())
        self.assertFalse(Report.objects.filter(target_job_id=self.job.pk).exists())
        self.assertFalse(Block.objects.filter(blocker_id=self.user.pk).exists())
        self.assertFalse(Block.objects.filter(blocked_id=self.user.pk).exists())
        self.assertFalse(Order.objects.filter(employer_id=self.user.pk).exists())
        self.assertFalse(Order.objects.filter(worker_id=self.user.pk).exists())

    def test_protected_orders_do_not_block_the_delete(self):
        """Order.employer/worker are PROTECT; deletion must still succeed."""
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(auth(self.user).delete(URL).status_code, 204)
        self.assertEqual(Order.objects.count(), 0)

    def test_resolved_by_is_nulled_not_cascaded(self):
        operator = make_user("+998900011003", role="operator")
        report = Report.objects.create(
            reporter=self.other, target_type="user", target_user=make_user("+998900011004"),
            reason="spam", status=Report.Status.RESOLVED,
            resolved_at=timezone.now(), resolved_by=operator,
        )
        delete_user_account(operator)

        report.refresh_from_db()
        self.assertIsNone(report.resolved_by)
        self.assertEqual(report.status, Report.Status.RESOLVED)


class DeleteLeavesOtherUsersAloneTests(TestCase):
    """Deleting A must not touch B."""

    def setUp(self):
        self.a = make_user("+998900012001", role="employer")
        self.b = make_user("+998900012002", role="employer")
        self.c = make_user("+998900012003")

        self.a_job = make_job(self.a, title="A ishi")
        self.b_job = make_job(self.b, title="B ishi")

        self.b_application = JobApplication.objects.create(
            job=self.b_job, worker=self.c, employer=self.b
        )
        self.b_report = Report.objects.create(
            reporter=self.b, target_type="user", target_user=self.c, reason="spam"
        )
        self.b_block = Block.objects.create(blocker=self.b, blocked=self.c)
        self.b_order = Order.objects.create(employer=self.b, worker=self.c, title="B order")

    def test_user_b_is_untouched(self):
        self.assertEqual(auth(self.a).delete(URL).status_code, 204)

        self.assertTrue(User.objects.filter(pk=self.b.pk).exists())
        self.assertTrue(Job.objects.filter(pk=self.b_job.pk).exists())
        self.assertTrue(JobApplication.objects.filter(pk=self.b_application.pk).exists())
        self.assertTrue(Report.objects.filter(pk=self.b_report.pk).exists())
        self.assertTrue(Block.objects.filter(pk=self.b_block.pk).exists())
        self.assertTrue(Order.objects.filter(pk=self.b_order.pk).exists())

        self.assertFalse(Job.objects.filter(pk=self.a_job.pk).exists())

    def test_b_can_still_use_the_api(self):
        auth(self.a).delete(URL)
        response = auth(self.b).get("/api/my-jobs/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([j["id"] for j in response.json()], [self.b_job.id])


class DeletedUserTokensTests(TestCase):
    """Old tokens must stop working. token_blacklist is not installed, so this
    rests on JWTAuthentication raising 'User not found' for a missing row."""

    def setUp(self):
        self.user = make_user("+998900013001")
        refresh = RefreshToken.for_user(self.user)
        self.access = str(refresh.access_token)
        self.refresh = str(refresh)

    def test_blacklist_app_is_not_installed(self):
        from django.conf import settings

        self.assertNotIn(
            "rest_framework_simplejwt.token_blacklist", settings.INSTALLED_APPS
        )

    def test_access_token_works_before_deletion(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        self.assertEqual(client.get(URL).status_code, 200)

    def test_access_token_is_401_after_deletion(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        self.assertEqual(client.delete(URL).status_code, 204)

        response = client.get(URL)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json().get("code"), "user_not_found")

    def test_refresh_works_before_deletion(self):
        response = APIClient().post(
            "/auth/refresh/", {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("access", response.json())

    def test_refresh_is_401_after_deletion_not_500(self):
        """simplejwt's own TokenRefreshSerializer 500s here (unguarded
        objects.get); SafeTokenRefreshView turns that into a clean 401 so the
        app logs out instead of treating it as a server fault."""
        delete_user_account(self.user)

        response = APIClient().post(
            "/auth/refresh/", {"refresh": self.refresh}, format="json"
        )
        self.assertEqual(response.status_code, 401, response.content)
        self.assertEqual(response.json().get("code"), "user_not_found")

    def test_dashboard_refresh_is_also_401_after_deletion(self):
        operator = make_user("+998900013002", role="operator")
        operator_refresh = str(RefreshToken.for_user(operator))
        delete_user_account(operator)

        response = APIClient().post(
            "/api/dashboard/auth/refresh/", {"refresh": operator_refresh}, format="json"
        )
        self.assertEqual(response.status_code, 401, response.content)


@override_settings(MEDIA_ROOT=None)  # replaced per-test below
class DeleteMediaTests(TestCase):
    """Uploaded files leave the disk, and a missing file is not an error."""

    def setUp(self):
        import tempfile

        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.user = make_user("+998900014001", role="employer")
        self.profile = WorkerProfile.objects.create(user=self.user, photo=tiny_png())
        self.job = make_job(self.user, photo1=tiny_png(), photo2=tiny_png())

    def _paths(self):
        return [
            self.profile.photo.path,
            self.job.photo1.path,
            self.job.photo2.path,
        ]

    def test_files_are_deleted_after_commit(self):
        import os

        for path in self._paths():
            self.assertTrue(os.path.exists(path), path)

        with self.captureOnCommitCallbacks(execute=True):
            auth(self.user).delete(URL)

        for path in self._paths():
            self.assertFalse(os.path.exists(path), path)

    def test_files_survive_until_the_transaction_commits(self):
        import os

        paths = self._paths()
        # Without executing the on_commit callbacks, nothing is unlinked.
        with self.captureOnCommitCallbacks(execute=False):
            auth(self.user).delete(URL)

        for path in paths:
            self.assertTrue(os.path.exists(path), path)

    def test_a_missing_file_does_not_fail_the_request(self):
        import os

        os.remove(self.job.photo1.path)  # file vanished behind the DB's back

        with self.captureOnCommitCallbacks(execute=True):
            response = auth(self.user).delete(URL)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_a_user_without_media_deletes_cleanly(self):
        plain = make_user("+998900014002")
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(auth(plain).delete(URL).status_code, 204)


class DeleteClearsOtpCacheTests(TestCase):
    PHONE = "+998900015001"

    def setUp(self):
        cache.clear()
        self.user = make_user(self.PHONE)

    def _seed(self):
        cache.set(otp_cache_key(self.PHONE), "somehash", 120)
        cache.set(otp_attempts_key(self.PHONE), 4, 120)
        cache.set(f"otp_send_cooldown:{self.PHONE}", 1, 60)
        cache.set(f"otp_send_hourly:{self.PHONE}", 5, 3600)

    def test_every_phone_keyed_entry_is_cleared(self):
        self._seed()
        with self.captureOnCommitCallbacks(execute=True):
            auth(self.user).delete(URL)

        self.assertIsNone(cache.get(otp_cache_key(self.PHONE)))
        self.assertIsNone(cache.get(otp_attempts_key(self.PHONE)))
        self.assertIsNone(cache.get(f"otp_send_cooldown:{self.PHONE}"))
        self.assertIsNone(cache.get(f"otp_send_hourly:{self.PHONE}"))

    def test_another_phones_keys_are_untouched(self):
        self._seed()
        cache.set(otp_attempts_key("+998900015002"), 3, 120)

        with self.captureOnCommitCallbacks(execute=True):
            auth(self.user).delete(URL)

        self.assertEqual(cache.get(otp_attempts_key("+998900015002")), 3)

    def test_a_locked_out_phone_is_not_locked_on_the_new_account(self):
        """A stale lockout must not follow the number onto a fresh account."""
        from apps.accounts.auth.otp import MAX_OTP_ATTEMPTS, send_otp, verify_otp

        cache.set(otp_attempts_key(self.PHONE), MAX_OTP_ATTEMPTS, 120)
        ok, err = verify_otp(self.PHONE, "123456")
        self.assertFalse(ok)
        self.assertIn("Too many attempts", err)

        with self.captureOnCommitCallbacks(execute=True):
            auth(self.user).delete(URL)

        code = send_otp(self.PHONE)
        self.assertTrue(verify_otp(self.PHONE, code)[0])


class ReRegisterAfterDeletionTests(TestCase):
    """Apple's reviewer will create -> delete -> log in again."""

    PHONE = "+998900016001"

    def setUp(self):
        cache.clear()

    def _login(self):
        from apps.accounts.auth.otp import send_otp

        code = send_otp(self.PHONE)
        return self.client.post(
            "/auth/verify-otp/", {"phone": self.PHONE, "code": code}, format="json"
        )

    def test_same_phone_creates_a_brand_new_empty_account(self):
        first = self._login()
        self.assertEqual(first.status_code, 200, first.content)
        self.assertIs(first.json()["created"], True)
        old_id = first.json()["user_id"]

        user = User.objects.get(pk=old_id)
        WorkerProfile.objects.create(user=user, first_name="Ali")
        make_job(user)

        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(auth(user).delete(URL).status_code, 204)

        second = self._login()
        self.assertEqual(second.status_code, 200, second.content)
        self.assertIs(second.json()["created"], True)

        new_id = second.json()["user_id"]
        self.assertNotEqual(new_id, old_id)

        fresh = User.objects.get(pk=new_id)
        self.assertFalse(WorkerProfile.objects.filter(user=fresh).exists())
        self.assertFalse(Job.objects.filter(employer=fresh).exists())
        self.assertIsNone(fresh.terms_accepted_at)
        self.assertEqual(fresh.terms_version, "")

    @override_settings(
        PLAY_REVIEW_PHONE=["+998900017001"], PLAY_REVIEW_OTP="424242", DEBUG=False
    )
    def test_play_reviewer_phone_can_delete_and_log_in_again(self):
        phone = "+998900017001"

        first = self.client.post(
            "/auth/verify-otp/", {"phone": phone, "code": "424242"}, format="json"
        )
        self.assertEqual(first.status_code, 200, first.content)
        user = User.objects.get(pk=first.json()["user_id"])

        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(auth(user).delete(URL).status_code, 204)

        # The bypass is keyed on the phone, not the user row, so it survives.
        second = self.client.post(
            "/auth/verify-otp/", {"phone": phone, "code": "424242"}, format="json"
        )
        self.assertEqual(second.status_code, 200, second.content)
        self.assertIs(second.json()["created"], True)
        self.assertNotEqual(second.json()["user_id"], first.json()["user_id"])

    @override_settings(
        PLAY_REVIEW_PHONE=["+998900018001", "+998900018002"],
        PLAY_REVIEW_OTP="424242",
    )
    def test_seed_play_review_recreates_a_deleted_reviewer(self):
        from django.core.management import call_command

        call_command("seed_play_review", stdout=io.StringIO())
        reviewer = User.objects.get(phone="+998900018001")
        employer = User.objects.get(phone="+998900018002")
        self.assertEqual(Job.objects.filter(employer=employer).count(), 3)

        with self.captureOnCommitCallbacks(execute=True):
            delete_user_account(reviewer)
            delete_user_account(employer)

        self.assertFalse(User.objects.filter(phone="+998900018001").exists())
        self.assertFalse(Job.objects.exists())

        # Re-seeding must rebuild both accounts and the demo jobs cleanly.
        call_command("seed_play_review", stdout=io.StringIO())

        reviewer = User.objects.get(phone="+998900018001")
        employer = User.objects.get(phone="+998900018002")
        self.assertEqual(reviewer.role, User.Role.WORKER)
        self.assertTrue(reviewer.worker_profile.is_completed)
        self.assertEqual(employer.role, User.Role.EMPLOYER)
        self.assertEqual(Job.objects.filter(employer=employer).count(), 3)

    @override_settings(
        PLAY_REVIEW_PHONE=["+998900019001", "+998900019002"],
        PLAY_REVIEW_OTP="424242",
    )
    def test_seed_play_review_is_idempotent(self):
        from django.core.management import call_command

        call_command("seed_play_review", stdout=io.StringIO())
        call_command("seed_play_review", stdout=io.StringIO())
        self.assertEqual(User.objects.filter(phone="+998900019002").count(), 1)
        self.assertEqual(Job.objects.count(), 3)


class DeleteServiceTests(TestCase):
    """The service itself, called directly (not through the endpoint)."""

    def test_returns_the_deleted_id(self):
        user = make_user("+998900020001")
        user_id = user.pk
        self.assertEqual(delete_user_account(user), user_id)

    def test_works_for_a_user_with_no_phone(self):
        user = User.objects.create_user(username="nophone", password="x")
        with self.captureOnCommitCallbacks(execute=True):
            delete_user_account(user)
        self.assertFalse(User.objects.filter(username="nophone").exists())
