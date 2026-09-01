# apps/jobs/geocode.py
"""Server-side reverse geocoding for the mobile "E'lon berish" flow.

GET /api/geocode/reverse/?lat=&lng=&lang= — proxies the Yandex Geocoder HTTP
API and maps the returned province onto the Job region slug. Failure-tolerant
by contract: any upstream problem still yields HTTP 200 with empty address
strings plus an "error" key, so the app is never blocked on Yandex.

Key: YANDEX_GEOCODER_API_KEY env var, falling back to the site's JS API key
(normally the same "JavaScript API and Geocoder HTTP API" product). Read here
via os.environ / getattr — settings.py is intentionally not touched.
"""
import logging
import math
import os
import re

import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

YANDEX_GEOCODER_URL = "https://geocode-maps.yandex.ru/1.x/"
GEOCODER_TIMEOUT = 4  # seconds
CACHE_TTL = 60 * 60 * 24  # 24 h; the app also debounces at 500 ms

# App lang → Yandex Geocoder lang. The JS API already runs with uz_UZ on the
# web picker; if the HTTP Geocoder rejects it or answers in Russian, switch
# the uz entry to "ru_RU" here.
LANG_MAP = {"uz": "uz_UZ", "ru": "ru_RU", "en": "en_US"}

# Yandex province name → Job region slug (slugs = UZ_REGIONS in
# apps/accounts/views.py). Keys are pre-normalized: lowercase, apostrophes and
# quotes stripped. Looked up twice — first the full name, then the name with
# generic admin words (viloyati/область/…) removed — so "toshkent viloyati"
# resolves before the bare "toshkent" (city) entry can match.
REGION_ALIASES = {
    # Tashkent city vs region — the one genuinely ambiguous pair.
    "toshkent shahri": "toshkent_city",
    "ташкент": "toshkent_city",
    "tashkent": "toshkent_city",
    "toshkent": "toshkent_city",
    "toshkent viloyati": "toshkent",
    "ташкентская область": "toshkent",
    "ташкентская": "toshkent",
    "tashkent region": "toshkent",
    "tashkent oblast": "toshkent",
    # Regions: uz latin (apostrophes already stripped) + ru adjectival forms.
    "andijon": "andijon", "андижанская": "andijon", "андижан": "andijon",
    "andijan region": "andijon",
    "fargona": "fargona", "ферганская": "fargona", "фергана": "fargona",
    "fergana region": "fargona",
    "namangan": "namangan", "наманганская": "namangan", "наманган": "namangan",
    "namangan region": "namangan",
    "samarqand": "samarqand", "самаркандская": "samarqand", "самарканд": "samarqand",
    "samarkand region": "samarqand",
    "buxoro": "buxoro", "бухарская": "buxoro", "бухара": "buxoro",
    "bukhara region": "buxoro",
    "navoiy": "navoiy", "навоийская": "navoiy", "навои": "navoiy",
    "navoiy region": "navoiy", "navoi region": "navoiy",
    "qashqadaryo": "qashqadaryo", "кашкадарьинская": "qashqadaryo",
    "кашкадарья": "qashqadaryo", "kashkadarya region": "qashqadaryo",
    "surxondaryo": "surxondaryo", "сурхандарьинская": "surxondaryo",
    "сурхандарья": "surxondaryo", "surkhandarya region": "surxondaryo",
    "xorazm": "xorazm", "хорезмская": "xorazm", "хорезм": "xorazm",
    "khorezm region": "xorazm",
    "jizzax": "jizzax", "джизакская": "jizzax", "джизак": "jizzax",
    "jizzakh region": "jizzax",
    "sirdaryo": "sirdaryo", "сырдарьинская": "sirdaryo", "сырдарья": "sirdaryo",
    "syrdarya region": "sirdaryo",
    "qoraqalpogiston": "qoraqalpogiston",
    "qoraqalpogiston respublikasi": "qoraqalpogiston",
    "республика каракалпакстан": "qoraqalpogiston",
    "каракалпакстан": "qoraqalpogiston",
    "republic of karakalpakstan": "qoraqalpogiston",
    "karakalpakstan": "qoraqalpogiston",
}

# Generic administrative words dropped for the second-pass lookup.
_ADMIN_WORDS = {
    "viloyati", "viloyat", "respublikasi", "respublika", "shahri",
    "область", "обл", "республика", "республикаси", "город",
    "region", "province", "oblast", "republic", "city", "of",
}

_APOSTROPHES = "'‘’ʻʼ`«»\"“”"


def _normalize(name):
    s = (name or "").strip().lower()
    s = s.translate({ord(c): None for c in _APOSTROPHES})
    return re.sub(r"\s+", " ", s).strip()


def region_slug_for(province):
    """Map a Yandex province name to a Job region slug.

    Returns the raw province name unchanged when nothing matches — the app
    then falls back to a manual region pick.
    """
    norm = _normalize(province)
    if not norm:
        return ""
    if norm in REGION_ALIASES:
        return REGION_ALIASES[norm]
    stripped = " ".join(w for w in norm.split() if w not in _ADMIN_WORDS)
    if stripped and stripped in REGION_ALIASES:
        return REGION_ALIASES[stripped]
    return province


def _geocoder_api_key():
    return (
        os.environ.get("YANDEX_GEOCODER_API_KEY", "").strip()
        or getattr(settings, "YANDEX_MAPS_API_KEY", "")
    )


def _empty_payload(lat, lng, error=None):
    out = {
        "lat": lat, "lng": lng,
        "region": "", "district": "", "street": "", "house": "",
        "formatted": "",
    }
    if error:
        out["error"] = error
    return out


def reverse_geocode(lat, lng, lang):
    """Reverse-geocode via Yandex. Never raises; on failure returns the empty
    payload with an "error" key (contract: the app must never be blocked)."""
    api_key = _geocoder_api_key()
    if not api_key:
        logger.warning("Reverse geocode skipped: no Yandex Geocoder API key configured.")
        return _empty_payload(lat, lng, error="no_api_key")

    yandex_lang = LANG_MAP.get(lang, LANG_MAP["uz"])
    cache_key = f"geocode:rev:{yandex_lang}:{round(lat, 4)}:{round(lng, 4)}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        resp = requests.get(
            YANDEX_GEOCODER_URL,
            params={
                "apikey": api_key,
                "geocode": f"{lng},{lat}",  # Yandex order: lon,lat
                "format": "json",
                "results": 1,
                "lang": yandex_lang,
            },
            timeout=GEOCODER_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.warning("Yandex Geocoder request failed: %s", exc)
        return _empty_payload(lat, lng, error="upstream_unreachable")

    if resp.status_code == 403:
        logger.warning("Yandex Geocoder returned 403 — check the API key / product.")
        return _empty_payload(lat, lng, error="upstream_forbidden")
    if resp.status_code != 200:
        logger.warning("Yandex Geocoder returned HTTP %s.", resp.status_code)
        return _empty_payload(lat, lng, error="upstream_error")

    try:
        members = (
            resp.json()["response"]["GeoObjectCollection"]["featureMember"]
        )
        if not members:
            # Valid response, just nothing there (open water etc.) — cacheable.
            payload = _empty_payload(lat, lng)
            cache.set(cache_key, payload, CACHE_TTL)
            return payload
        # First member of a reverse geocode = most specific object.
        meta = members[0]["GeoObject"]["metaDataProperty"]["GeocoderMetaData"]
        address = meta.get("Address", {})
        components = address.get("Components", [])
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        logger.warning("Yandex Geocoder response unparseable: %s", exc)
        return _empty_payload(lat, lng, error="upstream_error")

    by_kind = {}
    for comp in components:
        kind, name = comp.get("kind"), comp.get("name", "")
        if kind and kind not in by_kind:  # keep the first (most general) of a kind
            by_kind[kind] = name

    province = by_kind.get("province", "")
    # Yandex nests provinces (country → republic → region); when the first
    # "province" is generic (e.g. "Узбекистан"-level), the LAST one is the
    # actual region — walk components in reverse for the most specific.
    for comp in reversed(components):
        if comp.get("kind") == "province":
            province = comp.get("name", "")
            break

    payload = {
        "lat": lat,
        "lng": lng,
        "region": region_slug_for(province),
        # City districts come back as kind=district; rural tumans as kind=area;
        # fall back to the locality name so the field is rarely empty.
        "district": by_kind.get("district") or by_kind.get("area") or by_kind.get("locality") or "",
        "street": by_kind.get("street", ""),
        "house": by_kind.get("house", ""),
        "formatted": address.get("formatted", ""),
    }
    cache.set(cache_key, payload, CACHE_TTL)
    return payload


class GeocodeAnonThrottle(SimpleRateThrottle):
    """~60/min per client IP, authenticated or not. Rate lives here on the
    class (not in REST_FRAMEWORK settings) by design."""
    scope = "geocode"
    rate = "60/min"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class ReverseGeocodeAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # public endpoint; no JWT processing needed
    throttle_classes = [GeocodeAnonThrottle]

    def get(self, request):
        try:
            lat = float(request.query_params.get("lat", ""))
            lng = float(request.query_params.get("lng", ""))
        except (TypeError, ValueError):
            return Response({"detail": "lat and lng must be numbers."}, status=400)
        if not (math.isfinite(lat) and math.isfinite(lng)):
            return Response({"detail": "lat and lng must be finite."}, status=400)
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            return Response({"detail": "lat/lng out of range."}, status=400)

        lang = request.query_params.get("lang", "uz")
        return Response(reverse_geocode(lat, lng, lang))