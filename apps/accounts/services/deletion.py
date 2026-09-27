# apps/accounts/services/deletion.py
"""Permanent account deletion (App Store Guideline 5.1.1(v)).

This is a REAL deletion, not a deactivation: the User row and everything
hanging off it is removed, then the uploaded files are unlinked from disk.
An account deleted here is gone — logging in again with the same phone
creates a brand-new, empty account via the normal OTP flow.

What goes, and how:

  cascaded by user.delete()
    WorkerProfile, Job (and each Job's JobApplications), JobApplication as
    worker and as employer, moderation Report (as reporter and as target
    user) and Block (both directions), auth group/permission through-rows.

  deleted explicitly, first
    orders.Order rows where the user is employer or worker. Order.employer
    and Order.worker are on_delete=PROTECT, so user.delete() raises
    ProtectedError while any survive. See the TODO below.

  nulled automatically
    Order.cancelled_by, OrderStatusHistory.changed_by and Report.resolved_by
    on OTHER people's rows (all SET_NULL), so their history survives with the
    actor anonymised.

TODO(orders): Orders are currently created only by `manage.py seed_dashboard`
and by tests — no live app flow produces one — so deleting them costs a real
user nothing today. Once orders are genuinely created by employers and
workers, deleting them here would erase the COUNTERPARTY's contract history
too, which is wrong: user A's deletion must not remove user B's record of the
job B actually did. At that point switch to nullable FKs plus anonymisation:
make Order.employer/worker null=True, on_delete=SET_NULL, snapshot the
display name and phone onto the Order before nulling, and have this function
anonymise instead of delete. That is a migration, so it is deliberately not
done here.
"""

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q

from apps.accounts.auth.otp import otp_attempts_key, otp_cache_key

logger = logging.getLogger(__name__)


def _collect_media(user):
    """Every stored file belonging to `user`, as (storage, name) pairs.

    Collected BEFORE the DB rows go, because the paths only exist on the
    model instances. Returns plain tuples rather than FieldFile objects so
    nothing in the on_commit callback touches a deleted row.
    """
    files = []

    profile = getattr(user, "worker_profile", None)
    if profile is not None and profile.photo:
        files.append((profile.photo.storage, profile.photo.name))

    # Jobs this user posted; each carries up to four photos.
    for job in user.jobs.all():
        for field_name in ("photo1", "photo2", "photo3", "photo4"):
            field = getattr(job, field_name, None)
            if field:
                files.append((field.storage, field.name))

    return files


def _delete_media(files):
    """Unlink the collected files. Never raises.

    A missing file is not an error — the DB row is already gone and the
    account is deleted either way, so a failure here must not surface to the
    user or roll anything back (it runs after commit regardless).
    """
    for storage, name in files:
        if not name:
            continue
        try:
            storage.delete(name)
        except Exception:
            # FileSystemStorage.delete already swallows FileNotFoundError;
            # this catches permission errors, remote-storage hiccups, etc.
            logger.warning("Could not delete media file %s during account deletion", name)


def _clear_otp_cache(phone):
    """Drop every cache key keyed to this phone.

    Listed by exact name so a stale lockout or send-cooldown cannot follow a
    phone number onto the fresh account someone creates with it afterwards.
    Sources: otp_cache_key/otp_attempts_key in apps/accounts/auth/otp.py, and
    the throttle keys written by _check_send_throttle in
    apps/accounts/auth/api_views.py. The per-IP throttle key is deliberately
    left alone — it is not keyed to the phone.
    """
    if not phone:
        return
    cache.delete_many([
        otp_cache_key(phone),               # otp:<phone>
        otp_attempts_key(phone),            # otp_attempts:<phone>
        f"otp_send_cooldown:{phone}",
        f"otp_send_hourly:{phone}",
    ])


def _blacklist_tokens(user):
    """Blacklist the user's outstanding refresh tokens, when the app is installed.

    A no-op today: rest_framework_simplejwt.token_blacklist is not in
    INSTALLED_APPS, and it is not needed for correctness either — once the
    User row is gone, JWTAuthentication.get_user() raises AuthenticationFailed
    ("User not found") and every existing access and refresh token 401s. This
    exists so enabling the blacklist app later does the right thing without a
    second look at this function.
    """
    if "rest_framework_simplejwt.token_blacklist" not in settings.INSTALLED_APPS:
        return
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
    except Exception:
        # Never let token bookkeeping block the deletion the user asked for.
        logger.warning("Could not blacklist tokens for user %s during deletion", user.pk)


def delete_user_account(user):
    """Permanently delete `user` and everything belonging to them.

    Runs the database work in one transaction; media files are unlinked only
    after that transaction commits, so a rolled-back delete never destroys
    files belonging to a still-existing account.

    Returns the deleted user's id (the instance's pk is cleared by delete()).
    """
    from apps.orders.models import Order

    user_id = user.pk
    phone = getattr(user, "phone", None)
    media = _collect_media(user)

    with transaction.atomic():
        _blacklist_tokens(user)

        # Must precede user.delete(): both FKs are PROTECT. See TODO(orders).
        Order.objects.filter(Q(employer=user) | Q(worker=user)).delete()

        user.delete()

        # Only once the row is really gone — otherwise a rollback would leave
        # an existing account unable to receive a code until the TTL expired.
        transaction.on_commit(lambda: _clear_otp_cache(phone))
        transaction.on_commit(lambda: _delete_media(media))

    logger.info("Deleted account %s", user_id)
    return user_id
