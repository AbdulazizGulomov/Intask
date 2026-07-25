/* Employer job location picker — Yandex Maps 2.1, centre-pin (Taxi) pattern.
 *
 * Shared by employer_job_create.html and employer_job_edit.html via
 * templates/partials/_job_location_picker.html. Self-initialising: it looks for
 * a single [data-job-location] wrapper and wires everything from data-hooks.
 *
 * Contract preserved: the chosen point POSTs as hidden `lat`/`lng` (6 dp) and
 * the address POSTs as `address`. If Yandex fails to load, the address text
 * input stays usable and a visible lat/lng fallback is revealed.
 */
(function () {
  "use strict";

  var wrap = document.querySelector("[data-job-location]");
  if (!wrap) return;

  var TASHKENT = [41.2995, 69.2401]; // default centre [lat, lng]
  var DEFAULT_ZOOM = 12;
  var PLACE_ZOOM = 16;

  var initialLat = parseFloat(wrap.getAttribute("data-initial-lat"));
  var initialLng = parseFloat(wrap.getAttribute("data-initial-lng"));
  var hasInitial = isFinite(initialLat) && isFinite(initialLng);

  var mapEl = wrap.querySelector("[data-jlp-map]");
  var mapWrap = mapEl ? mapEl.parentElement : null;
  var addrInp = wrap.querySelector("[data-jlp-address]");
  var latInp = wrap.querySelector("[data-jlp-lat]");
  var lngInp = wrap.querySelector("[data-jlp-lng]");
  var geoBtn = wrap.querySelector("[data-jlp-geo]");
  var msgEl = wrap.querySelector("[data-jlp-msg]");
  var fbWrap = wrap.querySelector("[data-jlp-fallback]");
  var fbLat = wrap.querySelector("[data-jlp-lat-fb]");
  var fbLng = wrap.querySelector("[data-jlp-lng-fb]");

  var T = window.JLP_I18N || {};

  function setCoords(lat, lng) {
    latInp.value = Number(lat).toFixed(6);
    lngInp.value = Number(lng).toFixed(6);
  }

  // Seed hidden inputs from saved coords (edit) so a no-move save keeps them.
  if (hasInitial) setCoords(initialLat, initialLng);

  // ---------- graceful degradation ----------
  function revealFallback(reason) {
    if (!fbWrap || !fbWrap.hidden) return;
    fbWrap.hidden = false;
    if (mapWrap) mapWrap.style.display = "none";
    function sync() {
      if (fbLat.value !== "") latInp.value = fbLat.value;
      if (fbLng.value !== "") lngInp.value = fbLng.value;
    }
    fbLat.addEventListener("input", sync);
    fbLng.addEventListener("input", sync);
    if (latInp.value) fbLat.value = latInp.value;
    if (lngInp.value) fbLng.value = lngInp.value;
    // The address text input keeps working — it still POSTs as `address`.
    if (geoBtn) geoBtn.addEventListener("click", function () {
      useGeolocation(function (lat, lng) {
        fbLat.value = Number(lat).toFixed(6);
        fbLng.value = Number(lng).toFixed(6);
        setCoords(lat, lng);
      });
    });
    if (reason) console.warn("Yandex Maps unavailable:", reason);
  }

  // Shared geolocation helper (used by both map and fallback paths).
  function useGeolocation(onOk) {
    if (!navigator.geolocation) {
      if (msgEl) msgEl.textContent = T.noGeo || "";
      return;
    }
    if (geoBtn) geoBtn.disabled = true;
    if (msgEl) msgEl.textContent = "📍 " + (T.locating || "");
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        onOk(pos.coords.latitude, pos.coords.longitude);
        if (msgEl) msgEl.textContent = "✅ " + (T.located || "");
        if (geoBtn) geoBtn.disabled = false;
      },
      function (err) {
        // Quiet inline message; never block — the map/inputs stay usable.
        if (msgEl) msgEl.textContent = "ℹ️ " + (T.denied || "");
        if (geoBtn) geoBtn.disabled = false;
        console.warn("Geolocation denied/failed:", err && err.message);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  // ---------- boot ----------
  if (window.__ymapsFailed || typeof ymaps === "undefined") {
    // Give a late-loading script a brief chance before falling back.
    var waited = 0;
    var poll = setInterval(function () {
      if (typeof ymaps !== "undefined" && !window.__ymapsFailed) {
        clearInterval(poll);
        initMap();
      } else if (window.__ymapsFailed || (waited += 200) >= 4000) {
        clearInterval(poll);
        revealFallback("script did not load");
      }
    }, 200);
  } else {
    initMap();
  }

  function initMap() {
    ymaps.ready(function () {
      var map;
      var reverseTimer = null;
      var suppressForward = false; // guard (a): programmatic address writes
      var skipNextReverse = false; // guard (b): skip one reverse after a pick

      // Touch: disable one-finger drag + scroll-zoom so a one-finger swipe pans
      // the PAGE, not the map (two-finger zooms; the centre pin is fixed anyway).
      var isTouch = window.matchMedia("(pointer: coarse)").matches;
      var behaviors = isTouch ? ["dblClickZoom", "multiTouch"] : ["default"];

      try {
        map = new ymaps.Map(mapEl, {
          center: hasInitial ? [initialLat, initialLng] : TASHKENT,
          zoom: hasInitial ? PLACE_ZOOM : DEFAULT_ZOOM,
          controls: ["zoomControl"]
        }, { behaviors: behaviors });
      } catch (e) {
        revealFallback(e && e.message);
        return;
      }

      // The pin is a fixed HTML/CSS overlay at the map centre — no placemark.
      // The selected coordinate is ALWAYS map.getCenter().

      // Guard (a): programmatic writes to the address input must not re-trigger
      // the forward geocode. Wrap every programmatic write in the flag.
      function writeAddress(text) {
        suppressForward = true;
        addrInp.value = text || "";
        suppressForward = false;
      }

      function reverseGeocode() {
        ymaps.geocode(map.getCenter(), { results: 1 }).then(
          function (res) {
            var obj = res.geoObjects.get(0);
            writeAddress(obj ? obj.getAddressLine() : "");
          },
          function () { /* geocode failed: keep coords, leave address as-is */ }
        );
      }

      // ----- map -> input -----
      map.events.add("actionbegin", function () {
        if (mapWrap) mapWrap.classList.add("jlp-lift");
      });
      map.events.add("actionend", function () {
        if (mapWrap) mapWrap.classList.remove("jlp-lift");
        var c = map.getCenter();
        setCoords(c[0], c[1]);
        // Guard (b): a suggestion pick recentres the map, firing this handler.
        // Skip exactly one reverse so it can't overwrite the chosen address.
        if (skipNextReverse) { skipNextReverse = false; return; }
        if (reverseTimer) clearTimeout(reverseTimer);
        reverseTimer = setTimeout(reverseGeocode, 400); // debounce ~400ms
      });

      // On edit with saved coords but no saved address, fill it once. On create
      // we leave coords/address empty until the user actually picks a location.
      if (hasInitial && !(addrInp.value && addrInp.value.trim())) {
        reverseTimer = setTimeout(reverseGeocode, 400);
      }

      // ----- input -> map -----
      function geocodeAndCenter(query, opts) {
        opts = opts || {};
        query = (query || "").trim();
        if (!query) return;
        ymaps.geocode(query, { results: 1 }).then(
          function (res) {
            var obj = res.geoObjects.get(0);
            if (!obj) {
              if (msgEl) msgEl.textContent = "ℹ️ " + (T.notFound || "");
              return;
            }
            if (msgEl) msgEl.textContent = "";
            // Guard (b): keep the user's chosen text — skip the reverse that the
            // upcoming recentre (actionend) would otherwise fire.
            if (opts.keepAddress) skipNextReverse = true;
            map.setCenter(obj.geometry.getCoordinates(), Math.max(map.getZoom(), PLACE_ZOOM));
          },
          function () {
            if (msgEl) msgEl.textContent = "ℹ️ " + (T.searchErr || "");
          }
        );
      }

      // Address suggestions (real Uzbek addresses). Optional — guarded.
      try {
        var suggest = new ymaps.SuggestView(addrInp, { results: 6 });
        suggest.events.add("select", function (e) {
          var val = e.get("item").value;
          writeAddress(val);                            // guard (a)
          geocodeAndCenter(val, { keepAddress: true }); // guard (b)
        });
      } catch (e) { /* suggest is a nice-to-have; ignore if unavailable */ }

      // Enter = geocode typed text, for users who ignore the dropdown.
      addrInp.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          geocodeAndCenter(addrInp.value, { keepAddress: true });
        }
      });

      // If some external code ever dispatches input while we're writing
      // programmatically, guard (a) makes the forward path a no-op.
      addrInp.addEventListener("input", function () {
        if (suppressForward) return; // programmatic write — do nothing
        // User typing is handled by SuggestView (dropdown) + Enter; no action here.
      });

      // Geolocation button: recentre the map → actionend updates coords + address
      // through the same path (never blocks).
      if (geoBtn) geoBtn.addEventListener("click", function () {
        useGeolocation(function (lat, lng) {
          map.setCenter([lat, lng], Math.max(map.getZoom(), PLACE_ZOOM));
        });
      });
    });
  }
})();
