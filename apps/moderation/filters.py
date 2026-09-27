# apps/moderation/filters.py
"""Word-list content filter for user-generated text (App Store Guideline 1.2).

Applied to job titles/descriptions and order reviews. The lists themselves
live in wordlist.py so they can be extended without touching this logic.

Matching is deliberately simple and predictable:
  * input is lowercased, separator noise is stripped and leetspeak digits
    are folded back ("f.u.c.k", "sh1t", "$hit") so trivial evasion still
    trips the filter;
  * matches are anchored on word boundaries, so ordinary words containing a
    banned substring ("method", "assignment", "Scunthorpe") are NOT flagged;
  * an entry ending in "*" matches the stem plus any suffix, which is what
    Uzbek and Russian need.

This is a first-line filter, not a moderation system. Anything it misses is
caught by the report flow (apps.moderation.models.Report).
"""

import re
import unicodedata
from functools import lru_cache

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.moderation.wordlist import BANNED_WORDS

# Message shown to the user. Deliberately says WHY without repeating the
# offending word back at them.
REJECTION_MESSAGE = _(
    "This text contains language that is not allowed on InTask. "
    "Please remove any offensive, abusive or illegal content and try again."
)

# Leetspeak / homoglyph folding applied before matching. Keys are what a user
# might type to evade; values are what the word list actually contains.
_SUBSTITUTIONS = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "@": "a",
    "$": "s",
    "!": "i",
    # Curly apostrophes -> the straight one the Uzbek entries are written with
    # ("ko’tini" must match "ko'tini").
    "’": "'",
    "ʼ": "'",
    "`": "'",
}

# Characters dropped entirely before matching, so "f.u.c.k" and "с у к а"
# collapse to the plain word. Spaces are preserved because some entries are
# multi-word phrases; they are normalised to single spaces instead.
_NOISE = re.compile(r"[.\-_*+~^/\|]")
_WHITESPACE = re.compile(r"\s+")


def _normalise(text: str) -> str:
    """Lowercase, strip accents/noise and fold leetspeak, for matching only."""
    s = unicodedata.normalize("NFKC", str(text or "")).lower()
    s = "".join(_SUBSTITUTIONS.get(ch, ch) for ch in s)
    s = _NOISE.sub("", s)
    return _WHITESPACE.sub(" ", s).strip()


def banned_words() -> list[str]:
    """The active word list: the shipped lists plus any deployment additions."""
    extra = getattr(settings, "MODERATION_EXTRA_BANNED_WORDS", None) or []
    return list(BANNED_WORDS) + [str(w).lower() for w in extra]


@lru_cache(maxsize=1)
def _compiled(signature: tuple[str, ...]) -> re.Pattern:
    """One alternation regex over the whole word list.

    `signature` is the word list itself, so lru_cache rebuilds automatically
    when a test or a deployment changes MODERATION_EXTRA_BANNED_WORDS.
    """
    parts = []
    for raw in signature:
        entry = _normalise(raw.rstrip("*"))
        if not entry:
            continue
        stem = raw.endswith("*")
        # \b does not fire between a Cyrillic letter and a word char, but it
        # behaves correctly at the string/space edges we care about because
        # Python's re is Unicode-aware by default for str patterns.
        suffix = r"\w*" if stem else ""
        parts.append(rf"\b{re.escape(entry)}{suffix}\b")
    if not parts:
        # Match nothing rather than everything when the list is empty.
        return re.compile(r"(?!x)x")
    return re.compile("|".join(parts), re.UNICODE)


def find_banned_words(text: str) -> list[str]:
    """Every banned term present in `text`, de-duplicated, in first-seen order.

    Returns [] for empty input. Intended for logging and tests — user-facing
    errors use REJECTION_MESSAGE and never echo the matches back.
    """
    if not text:
        return []
    pattern = _compiled(tuple(banned_words()))
    seen = []
    for match in pattern.finditer(_normalise(text)):
        word = match.group(0)
        if word not in seen:
            seen.append(word)
    return seen


def contains_banned_words(text: str) -> bool:
    """True when `text` trips the filter."""
    return bool(find_banned_words(text))


def validate_clean_text(text: str, field_name: str = "text") -> None:
    """Raise DRF ValidationError keyed on `field_name` when `text` is dirty.

    Imported lazily inside callers that must not depend on DRF at import time.
    """
    from rest_framework.exceptions import ValidationError

    if contains_banned_words(text):
        raise ValidationError({field_name: [REJECTION_MESSAGE]})
