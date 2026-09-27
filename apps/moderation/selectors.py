# apps/moderation/selectors.py
"""Read helpers for applying blocks to other apps' querysets.

Blocking is SYMMETRIC: one Block row hides each party from the other. A user
who blocks someone must not see them, and must not be visible to them either
— otherwise blocking merely hides the harassment from the victim while
leaving them exposed to the person they blocked.
"""

from django.db.models import Q

from apps.moderation.models import Block


def blocked_user_ids(user) -> set[int]:
    """Every user id `user` must not see, and that must not see `user`.

    Union of both directions. Returns an empty set for anonymous users, so
    callers can apply it unconditionally to AllowAny endpoints.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return set()

    pairs = Block.objects.filter(
        Q(blocker_id=user.id) | Q(blocked_id=user.id)
    ).values_list("blocker_id", "blocked_id")

    ids = set()
    for blocker_id, blocked_id in pairs:
        ids.add(blocked_id if blocker_id == user.id else blocker_id)
    ids.discard(user.id)  # defensive: a self-block would hide the user's own data
    return ids


def is_blocked_between(user_a, user_b) -> bool:
    """True when a block exists in either direction between two users."""
    a_id = getattr(user_a, "id", user_a)
    b_id = getattr(user_b, "id", user_b)
    if not a_id or not b_id or a_id == b_id:
        return False
    return Block.objects.filter(
        Q(blocker_id=a_id, blocked_id=b_id) | Q(blocker_id=b_id, blocked_id=a_id)
    ).exists()


def exclude_blocked_jobs(qs, user):
    """Drop jobs posted by anyone blocked in either direction."""
    ids = blocked_user_ids(user)
    return qs.exclude(employer_id__in=ids) if ids else qs
