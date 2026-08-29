# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Intask (Task-in) — a Django 6 job marketplace for Uzbekistan connecting workers and employers. Auth is phone-number OTP via Eskiz SMS (no passwords for regular users); admins log in with username/password. UI is server-rendered Django templates; a small DRF/JWT API exists alongside for mobile.

## Commands

The virtualenv lives in `.venv/`. On Windows run Python as `.venv\Scripts\python.exe`.

```
.venv\Scripts\python.exe manage.py runserver          # dev server
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py makemigrations
.venv\Scripts\python.exe manage.py test               # all tests
.venv\Scripts\python.exe manage.py test apps.accounts.tests.SomeTest.test_name   # single test
.venv\Scripts\python.exe manage.py seed_professions   # seed Profession rows (custom command in apps/jobs)
.venv\Scripts\python.exe manage.py makemessages -l uz -l ru -l en   # i18n (locale/ dir; default language is uz)
.venv\Scripts\python.exe manage.py compilemessages
```

Runtime dependencies for local dev:
- **Redis at 127.0.0.1:6379/1** — the default cache backend. OTP codes and the Eskiz API token live in this cache, so the OTP login flow fails without Redis.
- `.env` in the repo root (loaded by python-dotenv) holds `ESKIZ_EMAIL`, `ESKIZ_PASSWORD`, `ESKIZ_FROM`, `ESKIZ_REAL_SMS`. With `ESKIZ_REAL_SMS=0` codes are generated and cached but no SMS is sent; set `FAKE_OTP_ENABLED = True` in settings to accept a fixed code (`111111`) without Redis lookup.

Note: `requirements.txt` is UTF-16 encoded (check encoding before appending with tools that write UTF-8). `STATIC_ROOT`/`MEDIA_ROOT` in settings point at production Linux paths (`/var/www/Intask/...`); DEBUG static/media serving is wired to those, so uploaded-media previews don't resolve on a Windows dev machine.

## Architecture

Single settings module `config/settings.py` (no dev/prod split — production values are edited in place; DEBUG is currently True with SQLite).

Two local apps under `apps/`:

- **`apps.accounts`** — custom user model (`AUTH_USER_MODEL = "accounts.User"`): `USERNAME_FIELD` is `phone`, with a `role` field (`worker` / `employer` / `admin`). OTP users get an unusable password. `WorkerProfile` (one-to-one with User) holds worker registration data and denormalizes `full_name` in `save()`. This app also owns almost all page views and URLs — including worker/employer home pages — not just auth.
- **`apps.jobs`** — `Profession`, `Job` (employer FK, region key string, pay range, up to 4 photos, lat/lng), `JobApplication` (unique per job+worker, pending/accepted/rejected).

### Auth and role flow (the part that spans files)

There are two parallel auth paths sharing the same OTP core (`apps/accounts/auth/otp.py`):

1. **Web (session)**: `views.otp_login` / `views.otp_verify_web` in `apps/accounts/views.py`. The chosen role is stashed in `request.session["user_role"]` *before* login (`choose_role`), then reconciled with `user.role` at OTP verification — an existing user's DB role wins; a new user gets the session role.
2. **API (JWT)**: `apps/accounts/auth/api_views.py` (`/auth/send-otp/`, `/auth/verify-otp/`, `/auth/refresh/`, `/me/`) using SimpleJWT bearer tokens.

Page-level access control is the `require_role(*roles)` decorator at the top of `apps/accounts/views.py` — it prefers `request.user.role`, falls back to the session role, and re-syncs the session. Use it (not `login_required`) for worker/employer pages.

OTP specifics: codes are 6 digits, cached under `otp:{phone}` with `OTP_TTL_SECONDS`, deleted on successful verify. `normalize_phone()` canonicalizes to `+998XXXXXXXXX` and returns `""` for anything non-Uzbek — callers must handle the empty string.

### URLs and templates

`config/urls.py` mounts `apps.accounts.urls` at the site root and `apps.jobs.urls` at `/jobs/`. Templates live in the root `templates/` directory (not per-app), extending `base.html`; static assets in root `static/`. i18n uses `LocaleMiddleware` + the `/i18n/` set-language view; user-visible strings should go through `gettext`/`{% trans %}` with translations in `locale/{uz,ru,en}/`.

`/privacy-policy/` and `/data-deletion/` must stay publicly reachable — Google Play listing requirement.
