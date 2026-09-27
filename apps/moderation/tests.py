"""UGC safety tests (App Store Guideline 1.2).

Covers terms acceptance, reporting, blocking (and its visibility effects),
the content filter, the operator moderation queue, and the cascade behaviour
account deletion relies on.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import WorkerProfile
from apps.jobs.models import Job, JobApplication
from apps.moderation.filters import contains_banned_words, find_banned_words
from apps.moderation.models import Block, Report
from apps.moderation.selectors import blocked_user_ids, is_blocked_between

User = get_user_model()


def make_user(phone, role="worker", **kwargs):
    return User.objects.create(phone=phone, role=role, **kwargs)


def make_job(employer, title="Elektrik kerak", **kwargs):
    defaults = {
        "region": "toshkent_city",
        "job_type": Job.JobType.HOURLY,
        "is_active": True,
    }
    defaults.update(kwargs)
    return Job.objects.create(employer=employer, title=title, **defaults)


def auth(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


# ===========================================================================
# 1. Terms / EULA acceptance
# ===========================================================================
class TermsAcceptanceTests(TestCase):
    URL = "/api/me/accept-terms/"

    def setUp(self):
        self.user = make_user("+998900001001")

    def test_me_exposes_terms_state_before_acceptance(self):
        data = auth(self.user).get("/api/me/").json()
        self.assertIsNone(data["terms_accepted_at"])
        self.assertEqual(data["terms_version"], "")
        # The app compares against this to decide whether to show the wall.
        self.assertEqual(data["terms_version_current"], "1.0")

    def test_accept_stamps_both_fields(self):
        before = timezone.now()
        response = auth(self.user).post(self.URL)
        self.assertEqual(response.status_code, 200, response.content)

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.terms_accepted_at)
        self.assertGreaterEqual(self.user.terms_accepted_at, before)
        self.assertEqual(self.user.terms_version, "1.0")

        body = response.json()
        self.assertEqual(body["terms_version"], "1.0")
        self.assertIsNotNone(body["terms_accepted_at"])

    def test_accepted_state_comes_back_from_me(self):
        client = auth(self.user)
        client.post(self.URL)
        data = client.get("/api/me/").json()
        self.assertIsNotNone(data["terms_accepted_at"])
        self.assertEqual(data["terms_version"], data["terms_version_current"])

    def test_accept_is_idempotent(self):
        client = auth(self.user)
        client.post(self.URL)
        self.user.refresh_from_db()
        first = self.user.terms_accepted_at

        response = client.post(self.URL)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        # Re-accepting refreshes the timestamp rather than erroring, so a
        # retry after a dropped response is safe.
        self.assertGreaterEqual(self.user.terms_accepted_at, first)

    def test_client_cannot_forge_version_or_timestamp(self):
        auth(self.user).post(
            self.URL, {"terms_version": "99.0", "terms_accepted_at": "2020-01-01T00:00:00Z"},
            format="json",
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.terms_version, "1.0")
        self.assertGreater(self.user.terms_accepted_at.year, 2020)

    def test_unauthenticated_is_401(self):
        self.assertEqual(APIClient().post(self.URL).status_code, 401)

    def test_terms_page_is_publicly_reachable(self):
        response = self.client.get("/terms/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "terms.html")


# ===========================================================================
# 2. Report
# ===========================================================================
class ReportAPITests(TestCase):
    URL = "/api/reports/"

    def setUp(self):
        self.reporter = make_user("+998900002001")
        self.offender = make_user("+998900002002", role="employer")
        self.job = make_job(self.offender)

    def test_report_a_user(self):
        response = auth(self.reporter).post(
            self.URL,
            {"target_type": "user", "target_user": self.offender.id, "reason": "abuse",
             "comment": "Kept sending threatening messages."},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        report = Report.objects.get()
        self.assertEqual(report.reporter, self.reporter)
        self.assertEqual(report.target_user, self.offender)
        self.assertIsNone(report.target_job)
        self.assertEqual(report.status, Report.Status.OPEN)
        self.assertIsNone(report.resolved_at)

    def test_report_a_job(self):
        response = auth(self.reporter).post(
            self.URL,
            {"target_type": "job", "target_job": self.job.id, "reason": "fraud"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        report = Report.objects.get()
        self.assertEqual(report.target_job, self.job)
        self.assertIsNone(report.target_user)

    def test_reporter_comes_from_the_token_not_the_body(self):
        auth(self.reporter).post(
            self.URL,
            {"target_type": "user", "target_user": self.offender.id,
             "reason": "spam", "reporter": self.offender.id},
            format="json",
        )
        self.assertEqual(Report.objects.get().reporter, self.reporter)

    def test_cannot_report_yourself(self):
        response = auth(self.reporter).post(
            self.URL,
            {"target_type": "user", "target_user": self.reporter.id, "reason": "spam"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("target_user", response.json())
        self.assertFalse(Report.objects.exists())

    def test_cannot_report_your_own_job(self):
        own_job = make_job(self.reporter, title="Mening ishim")
        response = auth(self.reporter).post(
            self.URL,
            {"target_type": "job", "target_job": own_job.id, "reason": "spam"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Report.objects.exists())

    def test_target_must_match_target_type(self):
        client = auth(self.reporter)
        missing = client.post(
            self.URL, {"target_type": "user", "reason": "spam"}, format="json"
        )
        self.assertEqual(missing.status_code, 400)
        self.assertIn("target_user", missing.json())

        mismatched = client.post(
            self.URL,
            {"target_type": "job", "target_user": self.offender.id,
             "target_job": self.job.id, "reason": "spam"},
            format="json",
        )
        self.assertEqual(mismatched.status_code, 400)

    def test_second_open_report_for_the_same_target_is_409(self):
        client = auth(self.reporter)
        payload = {"target_type": "user", "target_user": self.offender.id, "reason": "abuse"}
        self.assertEqual(client.post(self.URL, payload, format="json").status_code, 201)

        duplicate = client.post(self.URL, payload, format="json")
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(Report.objects.count(), 1)

    def test_can_report_again_once_the_first_is_closed(self):
        client = auth(self.reporter)
        payload = {"target_type": "user", "target_user": self.offender.id, "reason": "abuse"}
        client.post(self.URL, payload, format="json")

        Report.objects.update(status=Report.Status.RESOLVED, resolved_at=timezone.now())

        # A repeat offender must be reportable again.
        self.assertEqual(client.post(self.URL, payload, format="json").status_code, 201)
        self.assertEqual(Report.objects.count(), 2)

    def test_a_different_reporter_is_not_blocked_by_someone_elses_report(self):
        other = make_user("+998900002003")
        payload = {"target_type": "user", "target_user": self.offender.id, "reason": "abuse"}
        auth(self.reporter).post(self.URL, payload, format="json")
        self.assertEqual(auth(other).post(self.URL, payload, format="json").status_code, 201)
        self.assertEqual(Report.objects.count(), 2)

    def test_banned_language_in_the_comment_is_rejected(self):
        response = auth(self.reporter).post(
            self.URL,
            {"target_type": "user", "target_user": self.offender.id,
             "reason": "abuse", "comment": "this guy is a fucking bastard"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("comment", response.json())
        self.assertFalse(Report.objects.exists())

    def test_unauthenticated_is_401(self):
        response = APIClient().post(
            self.URL,
            {"target_type": "user", "target_user": self.offender.id, "reason": "spam"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)


# ===========================================================================
# 3. Block
# ===========================================================================
class BlockAPITests(TestCase):
    URL = "/api/blocks/"

    def setUp(self):
        self.alice = make_user("+998900003001")
        self.bob = make_user("+998900003002")
        WorkerProfile.objects.create(user=self.bob, first_name="Bob", last_name="Karimov")

    def test_block_then_list_then_unblock(self):
        client = auth(self.alice)

        created = client.post(self.URL, {"user_id": self.bob.id}, format="json")
        self.assertEqual(created.status_code, 201, created.content)
        self.assertTrue(Block.objects.filter(blocker=self.alice, blocked=self.bob).exists())

        listing = client.get(self.URL).json()
        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0]["id"], self.bob.id)
        self.assertEqual(listing[0]["full_name"], "Bob Karimov")
        self.assertIn("blocked_at", listing[0])

        removed = client.delete(f"{self.URL}{self.bob.id}/")
        self.assertEqual(removed.status_code, 204)
        self.assertFalse(Block.objects.exists())
        self.assertEqual(client.get(self.URL).json(), [])

    def test_blocking_twice_is_idempotent(self):
        client = auth(self.alice)
        self.assertEqual(client.post(self.URL, {"user_id": self.bob.id}, format="json").status_code, 201)
        again = client.post(self.URL, {"user_id": self.bob.id}, format="json")
        self.assertEqual(again.status_code, 200)
        self.assertIs(again.json()["created"], False)
        self.assertEqual(Block.objects.count(), 1)

    def test_unblocking_something_not_blocked_is_still_204(self):
        self.assertEqual(auth(self.alice).delete(f"{self.URL}{self.bob.id}/").status_code, 204)

    def test_cannot_block_yourself(self):
        response = auth(self.alice).post(self.URL, {"user_id": self.alice.id}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Block.objects.exists())

    def test_blocking_an_unknown_user_is_404(self):
        response = auth(self.alice).post(self.URL, {"user_id": 999999}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_missing_or_non_numeric_user_id_is_400(self):
        client = auth(self.alice)
        self.assertEqual(client.post(self.URL, {}, format="json").status_code, 400)
        self.assertEqual(client.post(self.URL, {"user_id": "abc"}, format="json").status_code, 400)

    def test_list_shows_only_my_own_blocks(self):
        Block.objects.create(blocker=self.bob, blocked=self.alice)
        # Bob blocked Alice; Alice's own list stays empty even though the block
        # affects her visibility.
        self.assertEqual(auth(self.alice).get(self.URL).json(), [])

    def test_unauthenticated_is_401(self):
        self.assertEqual(APIClient().get(self.URL).status_code, 401)
        self.assertEqual(APIClient().post(self.URL, {"user_id": 1}, format="json").status_code, 401)

    def test_selectors_are_symmetric(self):
        Block.objects.create(blocker=self.alice, blocked=self.bob)
        self.assertEqual(blocked_user_ids(self.alice), {self.bob.id})
        self.assertEqual(blocked_user_ids(self.bob), {self.alice.id})
        self.assertTrue(is_blocked_between(self.alice, self.bob))
        self.assertTrue(is_blocked_between(self.bob, self.alice))


# ===========================================================================
# 3b. Block visibility — the part Apple actually checks
# ===========================================================================
class BlockVisibilityTests(TestCase):
    """A block hides each party from the other in BOTH directions."""

    def setUp(self):
        self.alice = make_user("+998900004001", role="employer")
        self.bob = make_user("+998900004002", role="employer")
        self.carol = make_user("+998900004003", role="employer")

        self.alice_job = make_job(self.alice, title="Alice ishi")
        self.bob_job = make_job(self.bob, title="Bob ishi")
        self.carol_job = make_job(self.carol, title="Carol ishi")

        # Alice blocks Bob. Carol is the untouched control.
        Block.objects.create(blocker=self.alice, blocked=self.bob)

    def _job_ids(self, user):
        body = auth(user).get("/api/jobs/").json()
        return {row["id"] for row in body["results"]}

    def test_job_list_hides_the_blocked_party_both_ways(self):
        alice_sees = self._job_ids(self.alice)
        self.assertNotIn(self.bob_job.id, alice_sees)
        self.assertIn(self.carol_job.id, alice_sees)

        bob_sees = self._job_ids(self.bob)
        self.assertNotIn(self.alice_job.id, bob_sees)
        self.assertIn(self.carol_job.id, bob_sees)

    def test_uninvolved_user_and_anonymous_see_everything(self):
        carol_sees = self._job_ids(self.carol)
        self.assertIn(self.alice_job.id, carol_sees)
        self.assertIn(self.bob_job.id, carol_sees)

        anon = APIClient().get("/api/jobs/").json()
        self.assertEqual(len(anon["results"]), 3)

    def test_job_detail_is_404_both_ways(self):
        self.assertEqual(auth(self.alice).get(f"/api/jobs/{self.bob_job.id}/").status_code, 404)
        self.assertEqual(auth(self.bob).get(f"/api/jobs/{self.alice_job.id}/").status_code, 404)
        # Control: still reachable for everyone else.
        self.assertEqual(auth(self.carol).get(f"/api/jobs/{self.bob_job.id}/").status_code, 200)

    def test_cannot_apply_to_a_blocked_partys_job(self):
        self.assertEqual(auth(self.alice).post(f"/api/jobs/{self.bob_job.id}/apply/").status_code, 404)
        self.assertEqual(auth(self.bob).post(f"/api/jobs/{self.alice_job.id}/apply/").status_code, 404)
        self.assertFalse(JobApplication.objects.exists())

        allowed = auth(self.carol).post(f"/api/jobs/{self.bob_job.id}/apply/")
        self.assertEqual(allowed.status_code, 201)

    def test_my_applications_drops_a_blocked_employers_job(self):
        # Bob applies to Alice's job BEFORE the block exists between them.
        Block.objects.all().delete()
        JobApplication.objects.create(job=self.alice_job, worker=self.bob, employer=self.alice)
        JobApplication.objects.create(job=self.carol_job, worker=self.bob, employer=self.carol)
        self.assertEqual(len(auth(self.bob).get("/api/my-applications/").json()), 2)

        Block.objects.create(blocker=self.alice, blocked=self.bob)
        rows = auth(self.bob).get("/api/my-applications/").json()
        job_ids = {row["job"]["id"] for row in rows}
        self.assertNotIn(self.alice_job.id, job_ids)
        self.assertIn(self.carol_job.id, job_ids)

    def test_applicants_list_drops_a_blocked_worker(self):
        Block.objects.all().delete()
        JobApplication.objects.create(job=self.alice_job, worker=self.bob, employer=self.alice)
        JobApplication.objects.create(job=self.alice_job, worker=self.carol, employer=self.alice)

        url = f"/api/jobs/{self.alice_job.id}/applications/"
        self.assertEqual(len(auth(self.alice).get(url).json()), 2)

        Block.objects.create(blocker=self.alice, blocked=self.bob)
        worker_ids = {row["worker"]["id"] for row in auth(self.alice).get(url).json()}
        self.assertNotIn(self.bob.id, worker_ids)
        self.assertIn(self.carol.id, worker_ids)

    def test_web_job_list_and_detail_respect_blocks(self):
        client = APIClient()
        client.force_login(self.alice)

        listing = client.get("/worker/")
        self.assertEqual(listing.status_code, 200)
        titles = [j["title"] for j in listing.context["jobs"]]
        self.assertNotIn("Bob ishi", titles)
        self.assertIn("Carol ishi", titles)

        self.assertEqual(client.get(f"/worker/job/{self.bob_job.id}/").status_code, 404)
        self.assertEqual(client.get(f"/worker/job/{self.carol_job.id}/").status_code, 200)

    def test_unblocking_restores_visibility(self):
        auth(self.alice).delete(f"/api/blocks/{self.bob.id}/")
        self.assertIn(self.bob_job.id, self._job_ids(self.alice))
        self.assertIn(self.alice_job.id, self._job_ids(self.bob))


# ===========================================================================
# 4. Content filter
# ===========================================================================
class ContentFilterUnitTests(TestCase):
    def test_flags_each_language(self):
        self.assertTrue(contains_banned_words("this is fucking terrible"))
        self.assertTrue(contains_banned_words("Сука, блять"))
        self.assertTrue(contains_banned_words("jalablar kerak"))

    def test_ordinary_text_passes(self):
        for clean in [
            "Elektrik kerak, tajribali usta",
            "Santexnik - kran almashtirish",
            "I need a method for this assignment",
            "Требуется электрик на постоянную работу",
            "Uy tozalash, 3 xonali kvartira",
        ]:
            self.assertFalse(contains_banned_words(clean), clean)

    def test_does_not_false_positive_inside_longer_words(self):
        # "meth" is banned; "methodology" must not be.
        self.assertTrue(contains_banned_words("meth"))
        self.assertFalse(contains_banned_words("methodology and assignment"))

    def test_stems_catch_inflected_forms(self):
        self.assertTrue(contains_banned_words("хуйня"))
        self.assertTrue(contains_banned_words("наркотики"))

    def test_simple_evasion_still_trips(self):
        self.assertTrue(contains_banned_words("sh1t"))
        self.assertTrue(contains_banned_words("$hit"))
        self.assertTrue(contains_banned_words("f.u.c.k"))

    def test_empty_input_is_clean(self):
        for empty in ("", None, "   "):
            self.assertEqual(find_banned_words(empty), [])

    def test_extra_words_from_settings_are_honoured(self):
        self.assertFalse(contains_banned_words("bannedphrase"))
        with self.settings(MODERATION_EXTRA_BANNED_WORDS=["bannedphrase"]):
            self.assertTrue(contains_banned_words("a bannedphrase here"))


class ContentFilterJobTests(TestCase):
    """The filter on the paths that actually create jobs."""

    URL = "/api/jobs/create/"

    def setUp(self):
        self.employer = make_user("+998900005001", role="employer")

    def _create(self, **overrides):
        payload = {"title": "Elektrik kerak", "region": "toshkent_city", "job_type": "hourly"}
        payload.update(overrides)
        return auth(self.employer).post(self.URL, payload, format="json")

    def test_clean_job_is_created(self):
        self.assertEqual(self._create().status_code, 201)
        self.assertEqual(Job.objects.count(), 1)

    def test_banned_title_is_rejected(self):
        response = self._create(title="fucking elektrik kerak")
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.json())
        self.assertFalse(Job.objects.exists())

    def test_banned_description_is_rejected(self):
        response = self._create(description="Сука, звони быстрее")
        self.assertEqual(response.status_code, 400)
        self.assertIn("description", response.json())
        self.assertFalse(Job.objects.exists())

    def test_rejection_message_does_not_echo_the_banned_word(self):
        body = self._create(title="fucking elektrik").json()
        self.assertNotIn("fucking", str(body).lower())

    def test_web_form_applies_the_same_filter(self):
        from apps.jobs.forms import JobForm

        base = {"title": "Elektrik kerak", "region": "toshkent_city", "job_type": "hourly"}
        self.assertNotIn("title", JobForm(data=base).errors)

        dirty = JobForm(data={**base, "title": "fucking elektrik"})
        self.assertIn("title", dirty.errors)

        dirty_desc = JobForm(data={**base, "description": "jalablar kerak"})
        self.assertIn("description", dirty_desc.errors)


class ContentFilterReviewTests(TestCase):
    """Order reviews. There is no worker/employer review endpoint yet, so the
    filter lives on the model and on the one serializer that can write them."""

    def setUp(self):
        self.employer = make_user("+998900006001", role="employer")
        self.worker = make_user("+998900006002")
        self.operator = make_user("+998900006003", role="operator")
        from apps.orders.models import Order

        self.order = Order.objects.create(
            employer=self.employer, worker=self.worker, title="Elektr ishi"
        )

    def test_model_clean_rejects_a_dirty_review(self):
        from django.core.exceptions import ValidationError

        self.order.employer_review = "this worker is a fucking bastard"
        with self.assertRaises(ValidationError) as ctx:
            self.order.full_clean()
        self.assertIn("employer_review", ctx.exception.message_dict)

    def test_model_clean_accepts_a_normal_review(self):
        self.order.employer_review = "Ishni vaqtida va sifatli bajardi."
        self.order.worker_review = "Хороший заказчик, всё оплатил вовремя."
        self.order.full_clean()  # must not raise

    def test_dashboard_update_rejects_a_dirty_review(self):
        url = f"/api/dashboard/orders/{self.order.id}/"
        response = auth(self.operator).patch(
            url, {"employer_review": "fucking useless"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("employer_review", response.json())

        self.order.refresh_from_db()
        self.assertEqual(self.order.employer_review, "")

    def test_dashboard_update_accepts_a_clean_review(self):
        url = f"/api/dashboard/orders/{self.order.id}/"
        response = auth(self.operator).patch(
            url, {"worker_review": "Yaxshi ish, rahmat."}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.order.refresh_from_db()
        self.assertEqual(self.order.worker_review, "Yaxshi ish, rahmat.")


# ===========================================================================
# 5. Operator dashboard queue
# ===========================================================================
class ModerationDashboardTests(TestCase):
    URL = "/api/dashboard/reports/"

    def setUp(self):
        self.operator = make_user("+998900007001", role="operator")
        self.reporter = make_user("+998900007002")
        self.offender = make_user("+998900007003", role="employer")
        self.job = make_job(self.offender, title="Shubhali ish")

        self.fresh = Report.objects.create(
            reporter=self.reporter, target_type="user",
            target_user=self.offender, reason="spam",
        )
        self.stale = Report.objects.create(
            reporter=self.reporter, target_type="job",
            target_job=self.job, reason="fraud",
        )
        # auto_now_add means created_at has to be backdated via update().
        Report.objects.filter(pk=self.stale.pk).update(
            created_at=timezone.now() - timedelta(hours=30)
        )

    def test_requires_an_operator(self):
        self.assertEqual(APIClient().get(self.URL).status_code, 401)
        self.assertEqual(auth(self.reporter).get(self.URL).status_code, 403)
        self.assertEqual(auth(self.operator).get(self.URL).status_code, 200)

    def test_admin_may_also_access(self):
        admin = make_user("+998900007009", role="admin")
        self.assertEqual(auth(admin).get(self.URL).status_code, 200)

    def test_open_first_oldest_first(self):
        resolved = Report.objects.create(
            reporter=self.reporter, target_type="user",
            target_user=make_user("+998900007004"), reason="other",
            status=Report.Status.RESOLVED, resolved_at=timezone.now(),
        )
        rows = auth(self.operator).get(self.URL, {"status": ""}).json()["results"]
        ids = [row["id"] for row in rows]

        # Open ones first, and among them the oldest (most overdue) leads.
        self.assertEqual(ids[0], self.stale.id)
        self.assertEqual(ids[1], self.fresh.id)
        self.assertEqual(ids[-1], resolved.id)

    def test_hours_open_and_overdue_flag(self):
        rows = {r["id"]: r for r in auth(self.operator).get(self.URL).json()["results"]}

        stale = rows[self.stale.id]
        self.assertGreater(stale["hours_open"], 24)
        self.assertIs(stale["is_overdue"], True)
        self.assertEqual(stale["sla_hours"], 24)

        fresh = rows[self.fresh.id]
        self.assertLess(fresh["hours_open"], 1)
        self.assertIs(fresh["is_overdue"], False)

    def test_closed_reports_are_never_overdue(self):
        Report.objects.filter(pk=self.stale.pk).update(
            status=Report.Status.RESOLVED, resolved_at=timezone.now()
        )
        rows = {r["id"]: r for r in auth(self.operator).get(self.URL, {"status": ""}).json()["results"]}
        self.assertIs(rows[self.stale.id]["is_overdue"], False)

    def test_default_list_and_status_filter(self):
        all_rows = auth(self.operator).get(self.URL, {"status": "open"}).json()
        self.assertEqual(all_rows["count"], 2)

        Report.objects.filter(pk=self.fresh.pk).update(status=Report.Status.REJECTED)
        open_rows = auth(self.operator).get(self.URL, {"status": "open"}).json()
        self.assertEqual(open_rows["count"], 1)

    def test_resolve(self):
        response = auth(self.operator).post(f"{self.URL}{self.fresh.id}/resolve/")
        self.assertEqual(response.status_code, 200, response.content)

        self.fresh.refresh_from_db()
        self.assertEqual(self.fresh.status, Report.Status.RESOLVED)
        self.assertEqual(self.fresh.resolved_by, self.operator)
        self.assertIsNotNone(self.fresh.resolved_at)

    def test_reject(self):
        auth(self.operator).post(f"{self.URL}{self.fresh.id}/reject/")
        self.fresh.refresh_from_db()
        self.assertEqual(self.fresh.status, Report.Status.REJECTED)
        self.assertEqual(self.fresh.resolved_by, self.operator)

    def test_hide_job_deactivates_and_resolves(self):
        response = auth(self.operator).post(f"{self.URL}{self.stale.id}/hide-job/")
        self.assertEqual(response.status_code, 200, response.content)

        self.job.refresh_from_db()
        self.stale.refresh_from_db()
        self.assertFalse(self.job.is_active)
        self.assertEqual(self.stale.status, Report.Status.RESOLVED)

        # And the job really is gone from the public list.
        self.assertEqual(APIClient().get("/api/jobs/").json()["count"], 0)

    def test_hide_job_on_a_user_report_is_400(self):
        response = auth(self.operator).post(f"{self.URL}{self.fresh.id}/hide-job/")
        self.assertEqual(response.status_code, 400)
        self.fresh.refresh_from_db()
        self.assertEqual(self.fresh.status, Report.Status.OPEN)

    def test_deactivate_user_deactivates_and_resolves(self):
        response = auth(self.operator).post(f"{self.URL}{self.fresh.id}/deactivate-user/")
        self.assertEqual(response.status_code, 200, response.content)

        self.offender.refresh_from_db()
        self.fresh.refresh_from_db()
        self.assertFalse(self.offender.is_active)
        self.assertEqual(self.fresh.status, Report.Status.RESOLVED)

    def test_deactivate_user_on_a_job_report_targets_the_employer(self):
        auth(self.operator).post(f"{self.URL}{self.stale.id}/deactivate-user/")
        self.offender.refresh_from_db()
        self.assertFalse(self.offender.is_active)

    def test_cannot_deactivate_staff_or_operators(self):
        staff = make_user("+998900007005", role="worker", is_staff=True)
        report = Report.objects.create(
            reporter=self.reporter, target_type="user", target_user=staff, reason="abuse",
        )
        response = auth(self.operator).post(f"{self.URL}{report.id}/deactivate-user/")
        self.assertEqual(response.status_code, 403)

        staff.refresh_from_db()
        report.refresh_from_db()
        self.assertTrue(staff.is_active)
        self.assertEqual(report.status, Report.Status.OPEN)

    def test_actions_require_an_operator(self):
        response = auth(self.reporter).post(f"{self.URL}{self.fresh.id}/resolve/")
        self.assertEqual(response.status_code, 403)
        self.fresh.refresh_from_db()
        self.assertEqual(self.fresh.status, Report.Status.OPEN)

    def test_queue_is_not_block_filtered(self):
        """Operators must see reports between users who blocked each other."""
        Block.objects.create(blocker=self.reporter, blocked=self.offender)
        rows = auth(self.operator).get(self.URL).json()
        self.assertEqual(rows["count"], 2)


# ===========================================================================
# 6. Deletion cascades
# ===========================================================================
class ModerationCascadeTests(TestCase):
    """What account deletion relies on.

    delete_user_account() does not exist yet (it lands with the account-
    deletion work); these assert the FK behaviour it will depend on, via the
    plain user.delete() it will ultimately call.
    """

    def setUp(self):
        self.alice = make_user("+998900008001", role="employer")
        self.bob = make_user("+998900008002")
        self.operator = make_user("+998900008003", role="operator")
        self.job = make_job(self.alice)

    def test_deleting_the_reporter_removes_their_reports(self):
        Report.objects.create(
            reporter=self.bob, target_type="user", target_user=self.alice, reason="spam"
        )
        self.bob.delete()
        self.assertFalse(Report.objects.exists())

    def test_deleting_the_reported_user_removes_the_report(self):
        Report.objects.create(
            reporter=self.bob, target_type="user", target_user=self.alice, reason="spam"
        )
        self.alice.delete()
        self.assertFalse(Report.objects.exists())

    def test_deleting_a_reported_job_removes_the_report(self):
        Report.objects.create(
            reporter=self.bob, target_type="job", target_job=self.job, reason="fraud"
        )
        self.job.delete()
        self.assertFalse(Report.objects.exists())

    def test_deleting_the_job_owner_cascades_through_the_job(self):
        Report.objects.create(
            reporter=self.bob, target_type="job", target_job=self.job, reason="fraud"
        )
        self.alice.delete()
        self.assertFalse(Job.objects.exists())
        self.assertFalse(Report.objects.exists())

    def test_deleting_the_resolver_keeps_the_report(self):
        report = Report.objects.create(
            reporter=self.bob, target_type="user", target_user=self.alice, reason="spam",
            status=Report.Status.RESOLVED, resolved_at=timezone.now(),
            resolved_by=self.operator,
        )
        self.operator.delete()

        report.refresh_from_db()  # SET_NULL: the moderation record survives
        self.assertIsNone(report.resolved_by)
        self.assertEqual(report.status, Report.Status.RESOLVED)

    def test_deleting_either_side_removes_the_block(self):
        Block.objects.create(blocker=self.alice, blocked=self.bob)
        self.bob.delete()
        self.assertFalse(Block.objects.exists())

        carol = make_user("+998900008004")
        Block.objects.create(blocker=self.alice, blocked=carol)
        self.alice.delete()
        self.assertFalse(Block.objects.exists())

    def test_deleting_one_user_leaves_another_users_rows_intact(self):
        carol = make_user("+998900008005", role="employer")
        carol_job = make_job(carol, title="Carol ishi")
        keep = Report.objects.create(
            reporter=carol, target_type="job", target_job=carol_job, reason="other"
        )
        Block.objects.create(blocker=carol, blocked=self.operator)

        Report.objects.create(
            reporter=self.bob, target_type="user", target_user=self.alice, reason="spam"
        )
        self.bob.delete()

        self.assertTrue(Report.objects.filter(pk=keep.pk).exists())
        self.assertTrue(Block.objects.filter(blocker=carol).exists())
        self.assertTrue(Job.objects.filter(pk=carol_job.pk).exists())
