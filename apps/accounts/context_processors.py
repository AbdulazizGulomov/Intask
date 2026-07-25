# apps/accounts/context_processors.py
"""Template context for the shared logged-in header chip.

Exposes a single `nav_user` dict on every template so the header can render
the authenticated state (name, avatar, active-mode role badge, and which
dropdown actions to show) without each view having to build it. Returns
`{"nav_user": None}` for anonymous requests so templates fall back to the
Log in / Sign up buttons.

Capability logic (can_work / can_hire) is reused from views so this stays a
single source of truth with the require_capability decorator.
"""
import re

from django.conf import settings

from apps.accounts.views import user_can_work, user_can_hire, get_display_name


def nav_user(request):
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return {"nav_user": None}

    # Active UI mode: the stored role, kept in sync with the session on login.
    role = getattr(user, "role", None) or request.session.get("user_role") or "worker"

    # Avatar comes from the worker profile if one exists (employers may not).
    avatar_url = None
    wp = getattr(user, "worker_profile", None)
    if wp is not None and getattr(wp, "photo", None):
        try:
            avatar_url = wp.photo.url
        except Exception:
            avatar_url = None

    name = get_display_name(user)

    return {
        "nav_user": {
            "display_name": name,
            "phone": getattr(user, "phone", "") or "",
            "avatar_url": avatar_url,
            "initial": (name[:1] or "U").upper(),
            "role": role,
            "is_worker": role != "employer",
            # "Switch mode" only makes sense when the account can act in both
            # modes (has both capabilities) — a plain worker never sees it.
            "can_switch": bool(user_can_work(user) and user_can_hire(user)),
        }
    }


def support_contact(request):
    """Expose the single support phone to every template.

    `support_phone` is the human-readable form (e.g. "+998 71 200 00 00");
    `support_phone_href` is the same number stripped to a valid tel: target
    (a leading "+" plus digits), so display and link can never drift.
    """
    phone = getattr(settings, "SUPPORT_PHONE", "") or ""
    digits = re.sub(r"[^\d]", "", phone)
    href = ("+" + digits) if phone.strip().startswith("+") else digits
    return {
        "support_phone": phone,
        "support_phone_href": href,
    }
