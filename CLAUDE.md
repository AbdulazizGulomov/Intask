# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Intask (TaskiN) — a Django 6 job marketplace for Uzbekistan connecting workers and employers. Auth is phone-number OTP via Eskiz SMS (no passwords for regular users). Server-rendered Django templates for the product UI, a DRF/JWT JSON API under `/api/`, and a separate React operator dashboard in `dashboard-frontend/`.

**This repo is public** — secrets, Play-reviewer phone numbers, and OTP codes must only ever come from `.env` / server environment, never be hardcoded or committed.

## Commands

The virtualenv is `.venv/` (Python 3.14). On Windows run Python as `.venv\Scripts\python.exe`.

```
.venv\Scripts\python.exe manage.py runserver
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py test                # all tests
.venv\Scripts\python.exe manage.py test apps.accounts.tests.SomeTest.test_name   # single test
.venv\Scripts\python.exe manage.py seed_professions    # seed Profession rows
.venv\Scripts\python.exe manage.py seed_test_users     # seed the DEBUG-only OTP test accounts
.venv\Scripts\python.exe manage.py seed_play_review    # seed Google Play reviewer accounts
.venv\Scripts\python.exe manage.py seed_dashboard      # demo data for the operator dashboard
.venv\Scripts\python.exe manage.py aggregate_analytics # nightly DailyMetric rollup (idempotent)
.venv\Scripts\python.exe manage.py makemessages -l uz -l ru -l en
.venv\Scripts\python.exe manage.py compilemessages
```

Operator dashboard frontend (React 19 + Vite, consumes `/api/dashboard/`):

```
cd dashboard-frontend
npm run dev / npm run build / npm run lint
```

### Environment switches (all in `.env`, loaded by python-dotenv)

- `DJANGO_DEBUG=1` — required for local dev: with DEBUG off, `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` become mandatory (fail-fast) and secure-cookie/HSTS settings switch on.
- `DB_NAME` set → Postgres + DatabaseCache (`django_cache` table — run `manage.py createcachetable` once). Unset → SQLite + LocMemCache. Note LocMemCache is per-process: OTP verify must hit the same process that sent the code.
- `ESKIZ_EMAIL` / `ESKIZ_PASSWORD` / `ESKIZ_FROM` / `ESKIZ_REAL_SMS` — real SMS sending; leave `ESKIZ_REAL_SMS=0` locally.
- `PLAY_REVIEW_PHONE` / `PLAY_REVIEW_OTP` — Google Play reviewer login bypass (active even with DEBUG off; disabled unless both are set).
- `YANDEX_MAPS_API_KEY` — map on employer job-create page; empty is fine locally.

Local OTP testing without SMS: with DEBUG on, the numbers in `OTP_TEST_NUMBERS` (settings.py) accept code `123456` — a returning worker, returning employer, fresh registration, and admin. Seed the returning users with `seed_test_users`.

`STATIC_ROOT`/`MEDIA_ROOT` point at production Linux paths (`/var/www/Intask/...`); the app runs behind nginx which terminates TLS.

## Architecture

Four local apps under `apps/`:

- **`apps.accounts`** — custom user model (`USERNAME_FIELD = phone`, roles worker/employer/admin), all product page views/URLs (worker and employer home pages included), the OTP core, and `dashboard/` — a DRF sub-package (`api_views`, `serializers`, `permissions`, `urls`) serving the operator dashboard API at `/api/dashboard/`.
- **`apps.jobs`** — `Profession`, `Job`, `JobApplication`, plus `api.py` with the public DRF views mounted in `config/urls.py` under `/api/jobs/`, `/api/my-jobs/`, etc.
- **`apps.orders`** — `Order`: a real work contract created when a JobApplication is accepted (scheduled → in_progress → completed/cancelled/disputed).
- **`apps.analytics`** — `DailyMetric`: pre-aggregated per-day/per-district rollup (cohort by order-created date; stores additive components, never rates). Populated by `aggregate_analytics`.

Root-level `*.py` scripts (`translate_all.py`, `fix_assets.py`, …) are historical one-off helpers, not part of the app.

### Auth: OTP core (`apps/accounts/auth/otp.py`)

Security-sensitive and deliberately layered — preserve these invariants when touching it:

- Codes are generated with `secrets`, stored in cache **only as an HMAC-SHA256 hash** keyed with `SECRET_KEY`, TTL `OTP_TTL_SECONDS` (120s), compared constant-time.
- 5-attempt lockout per phone (`otp_attempts:{phone}`), counted atomically with `cache.add` + `cache.incr`. The counter is **not** cleared when a new code is sent — only on successful verify or expiry — so lockout can't be reset by requesting a new code.
- `verify_otp` returns a `(ok, error_message)` tuple, not a bool.
- Special branches, in order: Play reviewer phones (env-driven fixed code, no SMS, no cache write, same lockout mechanics, works in production), then DEBUG-only `OTP_TEST_NUMBERS` (same storage path as real codes), then the normal path. Reviewer bypass fails closed if either env var is missing.

Two parallel login paths share this core: web session views (`otp_login` / `otp_verify_web` in `apps/accounts/views.py`) and the JWT API (`apps/accounts/auth/api_views.py` → `/auth/send-otp/`, `/auth/verify-otp/`, `/auth/refresh/`).

### Roles vs. capabilities (dual-mode users)

`User.role` is only the **default UI mode**; real access control is capability-based. `User.can_hire` is a flag letting a worker also post jobs (`/api/me/become-employer/` sets it). The single sources of truth are `user_can_work()` / `user_can_hire()` in `apps/accounts/views.py`, enforced by the `require_capability(*caps)` decorator — use it for new worker/employer pages instead of `require_role`, which locks dual-capability users out of the "wrong" mode. The header chip's mode switching comes from the same functions via the `nav_user` context processor.

### Templates and context processors

Root `templates/` dir; `base_site.html` is the shared page shell, reusable fragments live in `templates/partials/` (`_head_meta.html`, `_user_chip.html`, `lang_switcher.html`, …). Two context processors run on every request (`apps/accounts/context_processors.py`): `nav_user` (header auth chip) and `support_contact` (exposes `SUPPORT_PHONE` from settings as `support_phone` / `support_phone_href` — never hardcode the support number in templates).

i18n: uz (default) / ru / en via `LocaleMiddleware` and the `/i18n/` set-language view; user-visible strings go through `gettext` / `{% trans %}` with catalogs in `locale/`.

`/privacy-policy/` and `/data-deletion/` must stay publicly reachable — Google Play listing requirement.
