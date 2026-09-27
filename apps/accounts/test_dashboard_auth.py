"""Operator dashboard auth tests.

Specifically the logout regression: token_blacklist is not installed, so
RefreshToken has no blacklist() method and the old call raised AttributeError
past the `except TokenError`, 500ing every logout.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

URL = "/api/dashboard/auth/logout/"


def make_operator(phone="+998900030001", role="operator"):
    user = User.objects.create(phone=phone, role=role)
    user.set_password("Str0ng-Passw0rd!")
    user.save()
    return user


def auth(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class OperatorLogoutTests(TestCase):
    def setUp(self):
        self.operator = make_operator()
        self.refresh = str(RefreshToken.for_user(self.operator))

    def test_blacklist_app_is_not_installed(self):
        """The precondition the fix exists for."""
        from django.conf import settings

        self.assertNotIn(
            "rest_framework_simplejwt.token_blacklist", settings.INSTALLED_APPS
        )
        self.assertFalse(hasattr(RefreshToken.for_user(self.operator), "blacklist"))

    def test_logout_returns_205_not_500(self):
        response = auth(self.operator).post(URL, {"refresh": self.refresh}, format="json")
        self.assertEqual(response.status_code, 205, response.content)

    def test_logout_without_a_refresh_token_is_400(self):
        response = auth(self.operator).post(URL, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_logout_with_a_garbage_token_is_still_205(self):
        """An already-expired or malformed token means the session is gone
        anyway — the client should not be left unable to log out."""
        response = auth(self.operator).post(URL, {"refresh": "not-a-jwt"}, format="json")
        self.assertEqual(response.status_code, 205, response.content)

    def test_logout_requires_authentication(self):
        response = APIClient().post(URL, {"refresh": self.refresh}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_admin_can_also_log_out(self):
        admin = make_operator("+998900030002", role="admin")
        refresh = str(RefreshToken.for_user(admin))
        response = auth(admin).post(URL, {"refresh": refresh}, format="json")
        self.assertEqual(response.status_code, 205, response.content)
