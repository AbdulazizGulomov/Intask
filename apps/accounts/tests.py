from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import WorkerProfile
from apps.jobs.models import Profession


class MeIsCompletedTests(TestCase):
    """/api/me/ -> is_completed: workers need name + profession + phone,
    employers need company name (WorkerProfile.first_name) + phone."""
    URL = "/api/me/"

    def setUp(self):
        self.profession = Profession.objects.create(name="Elektrik")

    def _me(self, user):
        c = APIClient()
        c.force_authenticate(user)
        r = c.get(self.URL)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_worker_without_profile_is_incomplete(self):
        user = get_user_model().objects.create(phone="+998900000031", role="worker")
        data = self._me(user)
        self.assertIs(data["is_completed"], False)
        # existing shape is untouched
        for key in ("id", "phone", "role", "first_name", "profession", "can_work", "can_hire"):
            self.assertIn(key, data)

    def test_worker_needs_name_and_profession(self):
        user = get_user_model().objects.create(phone="+998900000032", role="worker")
        wp = WorkerProfile.objects.create(user=user, first_name="Bekzod")
        self.assertIs(self._me(user)["is_completed"], False)  # no profession yet
        wp.profession = self.profession
        wp.save()
        self.assertIs(self._me(user)["is_completed"], True)
        wp.first_name = ""
        wp.save()
        self.assertIs(self._me(user)["is_completed"], False)  # name gone

    def test_worker_without_phone_is_incomplete(self):
        user = get_user_model().objects.create_user(username="nophone", password="x", role="worker")
        WorkerProfile.objects.create(user=user, first_name="Bekzod", profession=self.profession)
        self.assertIs(self._me(user)["is_completed"], False)

    def test_stored_flag_does_not_short_circuit_the_rule(self):
        user = get_user_model().objects.create(phone="+998900000033", role="worker")
        WorkerProfile.objects.create(user=user, first_name="Bekzod", is_completed=True)
        self.assertIs(self._me(user)["is_completed"], False)  # web flag set, no profession

    def test_employer_needs_company_name_and_phone(self):
        user = get_user_model().objects.create(phone="+998900000034", role="employer")
        self.assertIs(self._me(user)["is_completed"], False)
        WorkerProfile.objects.create(user=user, first_name="Anvar Logistika")
        self.assertIs(self._me(user)["is_completed"], True)  # no profession required
