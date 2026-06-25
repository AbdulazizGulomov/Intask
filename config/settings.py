from pathlib import Path
from datetime import timedelta
import os

from dotenv import load_dotenv

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Env-driven; defaults to False so production is safe unless DJANGO_DEBUG=1 is set.
# Computed first so the security config below can branch on it.
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"

# SECRET_KEY: required in production. A clearly-labelled dev-only fallback is used
# under DEBUG; in production an unset key fails fast rather than running insecure.
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-only-not-for-production"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DEBUG is off.")

# ALLOWED_HOSTS from env (comma-separated). Local dev defaults to loopback only;
# production must supply DJANGO_ALLOWED_HOSTS (no wildcard).
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
if not ALLOWED_HOSTS and DEBUG:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Secure transport — production only (must not break local DEBUG over HTTP).
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # App runs behind nginx, which terminates TLS and sets X-Forwarded-Proto.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # SECURE_SSL_REDIRECT intentionally left off: nginx already forces HTTPS, so
    # redirecting here would risk a loop behind the proxy.

# =====================
# Internationalization
# =====================
USE_I18N = True
USE_TZ = True

LANGUAGE_CODE = "uz"

LANGUAGES = [
    ("uz", "Uzbek"),
    ("ru", "Russian"),
    ("en", "English"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

LANGUAGE_COOKIE_NAME = "django_language"
TIME_ZONE = "Asia/Tashkent"

# =====================
# Applications
# =====================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # third-party
    "rest_framework",

    # local apps
    "apps.accounts.apps.AccountsConfig",
    "apps.jobs.apps.JobsConfig",
    "apps.orders.apps.OrdersConfig",
    "apps.analytics.apps.AnalyticsConfig",
]

# =====================
# Media / Static
# =====================
MEDIA_URL = "/media/"
MEDIA_ROOT = "/var/www/Intask/Task_in/media"

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = "/var/www/Intask/Task_in/staticfiles"

# =====================
# Middleware
# =====================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# =====================
# Templates
# =====================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# =====================
# Database
# =====================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# =====================
# Auth
# =====================
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/otp/"

# =====================
# Cache / OTP
# =====================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "taskin-otp-cache",
    }
}

OTP_TTL_SECONDS = 120

# OTP behavior
FAKE_OTP_ENABLED = False
OTP_DEBUG_RETURN_CODE = False
ESKIZ_REAL_SMS = True

# DEBUG-ONLY fixed test numbers → deterministic OTP code, no SMS. These are
# obviously-fake reserved numbers (still pass the +998+9-digit validator). The
# bypass in send_otp() is gated on settings.DEBUG, so this is INERT in production
# (when DEBUG=False those numbers get the normal real OTP path). Seed the
# "returning" users with: manage.py seed_test_users
OTP_TEST_NUMBERS = {
    "+998900000001": "123456",   # returning worker (complete profile → /worker/)
    "+998900000002": "123456",   # returning employer (→ /employer/)
    "+998900000003": "123456",   # fresh — first-time register (intentionally unseeded → /role/)
}

# Eskiz SMS settings from .env
ESKIZ_EMAIL = os.getenv("ESKIZ_EMAIL", "")
ESKIZ_PASSWORD = os.getenv("ESKIZ_PASSWORD", "")
ESKIZ_FROM = os.getenv("ESKIZ_FROM", "4546")
ESKIZ_REAL_SMS = os.getenv("ESKIZ_REAL_SMS", "0") == "1"

# =====================
# DRF / JWT
# =====================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}
