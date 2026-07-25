/* Employer job location picker — Yandex Maps 2.1, centre-pin with an explicit
 * confirm step (Yandex Taxi style).
 *
 * Shared by employer_job_create.html and employer_job_edit.html via
 * templates/partials/_job_location_picker.html.
 *
 * Commit model: panning only PREVIEWS the reverse-geocoded address (muted strip);
 * nothing is written to the `address` field or the hidden lat/lng until the user
 * presses "Tasdiqlash". "O'zgartirish" returns to the unconfirmed state. Typed
 * suggestions and geolocation also feed the preview only.
 *
 * Contract preserved: chosen point POSTs as hidden `lat`/`lng` (6 dp), address
 * POSTs as `address`. Yandex-load failure reveals an editable lat/lng fallback
 * and keeps the address input usable.
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
  var searchWrap = wrap.querySelector("[data-jlp-search]");
  var latInp = wrap.querySelector("[data-jlp-lat]");
  var lngInp = wrap.querySelector("[data-jlp-lng]");
  var geoBtn = wrap.querySelector("[data-jlp-geo]");
  var msgEl = wrap.querySelector("[data-jlp-msg]");
  var previewEl = wrap.querySelector("[data-jlp-preview]");
  var previewAddrEl = wrap.querySelector("[data-jlp-preview-addr]");
  var confirmBtn = wrap.querySelector("[data-jlp-confirm]");
  var confirmedBlock = wrap.querySelector("[data-jlp-confirmed]");
  var confirmedAddrEl = wrap.querySelector("[data-jlp-confirmed-addr]");
  var changeBtn = wrap.querySelector("[data-jlp-change]");
  var warnEl = wrap.querySelector("[data-jlp-warn]");
  var fbWrap = wrap.querySelector("[data-jlp-fallback]");
  var fbLat = wrap.querySelector("[data-jlp-lat-fb]");
  var fbLng = wrap.querySelector("[data-jlp-lng-fb]");

  var T = window.JLP_I18N || {};

  function setCoords(lat, lng) {
    latInp.value = Number(lat).toFixed(6);
    lngInp.value = Number(lng).toFixed(6);
  }
  function clearCoords() { latInp.value = ""; lngInp.value = ""; }

  // ---------- graceful degradation ----------
  function revealFallback(reason) {
    if (!fbWrap || !fbWrap.hidden) return;
    fbWrap.hidden = false;
    if (mapWrap) mapWrap.style.display = "none";
    // The confirm-flow UI is meaningless without a map — hide it. The address
    // text input stays usable and still POSTs as `address`.
    if (previewEl) previewEl.hidden = true;
    if (confirmBtn) confirmBtn.style.display = "none";
    if (confirmedBlock) confirmedBlock.hidden = true;
    if (searchWrap) searchWrap.hidden = false;

    function sync() {
      if (fbLat.value !== "") latInp.value = fbLat.value;
      if (fbLng.value !== "") lngInp.value = fbLng.value;
    }
    fbLat.addEventListener("input", sync);
    fbLng.addEventListener("input", sync);
    if (latInp.value) fbLat.value = latInp.value;
    if (lngInp.value) fbLng.value = lngInp.value;
    if (geoBtn) geoBtn.addEventListener("click", function () {
      useGeolocation(function (lat, lng) {
        fbLat.value = Number(lat).toFixed(6);
        fbLng.value = Number(lng).toFixed(6);
        setCoords(lat, lng);
      });
    });
    if (reason) console.warn("Yandex Maps unavailable:", reason);
  }

  function useGeolocation(onOk) {
    if (!navigator.geolocation) {
      if (msgEl) msgEl.textContent = T.noGeo || "";
      return;
    }
    if (geoBtn) geoBtn.disabled = true;
    if (msgEl) msgEl.textContent = "📍 " + (T.locating || "");
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        if (msgEl) msgEl.textContent = ""; // no "added" status — commit is explicit now
        if (geoBtn) geoBtn.disabled = false;
        onOk(pos.coords.latitude, pos.coords.longitude);
      },
      function (err) {
        if (msgEl) msgEl.textContent = "ℹ️ " + (T.denied || "");
        if (geoBtn) geoBtn.disabled = false;
        console.warn("Geolocation denied/failed:", err && err.message);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  // ---------- boot ----------
  if (window.__ymapsFailed || typeof ymaps === "undefined") {
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

      // State: nothing is committed until the user presses Tasdiqlash.
      var confirmed = false;
      var previewAddress = "";   // last reverse-geocoded / chosen preview text
      var previewCoords = null;  // [lat, lng] matching previewAddress

      var isTouch = window.matchMedia("(pointer: coarse)").matches;
      var behaviors = isTouch ? ["dblClickZoom", "multiTouch"] : ["default"];

      try {
        map = new ymaps.Map(mapEl, {
          center: hasInitial ? [initialLat, initialLng] : TASHKENT,
          zoom: hasInitial ? PLACE_ZOOM : DEFAULT_ZOOM,
          controls: ["zoomControl"]
        }, {
          behaviors: behaviors,
          // Remove the "Open in Yandex.Maps" block — on a form it's a way to lose
          // a half-filled submission.
          suppressMapOpenBlock: true
        });
      } catch (e) {
        revealFallback(e && e.message);
        return;
      }

      // Guard (a): programmatic writes to the address field must not re-trigger
      // the forward geocode.
      function writeAddress(text) {
        suppressForward = true;
        addrInp.value = text || "";
        suppressForward = false;
      }

      // ---------- preview (never commits) ----------
      function showPreview(text, coords) {
        previewAddress = text || "";
        previewCoords = coords || map.getCenter();
        if (previewAddrEl) previewAddrEl.textContent = previewAddress;
        if (previewEl) previewEl.hidden = !previewAddress;
        // Confirm is available only while unconfirmed and a preview exists.
        if (confirmBtn && !confirmed) confirmBtn.disabled = !previewAddress;
      }

      function reverseGeocodePreview() {
        var c = map.getCenter();
        ymaps.geocode(c, { results: 1 }).then(
          function (res) {
            var obj = res.geoObjects.get(0);
            showPreview(obj ? obj.getAddressLine() : "", c);
          },
          function () { /* geocode failed: leave the previous preview */ }
        );
      }

      // ---------- state transitions ----------
      function enterConfirmed(addr, coords) {
        confirmed = true;
        writeAddress(addr);                 // commit address (guard a)
        setCoords(coords[0], coords[1]);    // commit coords
        if (confirmedAddrEl) confirmedAddrEl.textContent = addr;
        if (confirmedBlock) confirmedBlock.hidden = false;
        if (searchWrap) searchWrap.hidden = true;
        if (confirmBtn) confirmBtn.style.display = "none";
        if (warnEl) warnEl.hidden = true;   // clear any prior submit warning
      }

      function enterUnconfirmed() {
        confirmed = false;
        clearCoords();                      // uncommit — nothing chosen now
        writeAddress("");                   // clear committed address (guard a)
        if (confirmedBlock) confirmedBlock.hidden = true;
        if (searchWrap) searchWrap.hidden = false;
        if (confirmBtn) {
          confirmBtn.style.display = "";
          confirmBtn.disabled = !previewAddress;
        }
      }

      // ---------- map -> preview ----------
      map.events.add("actionbegin", function () {
        if (mapWrap) mapWrap.classList.add("jlp-lift");
      });
      map.events.add("actionend", function () {
        if (mapWrap) mapWrap.classList.remove("jlp-lift");
        // Guard (b): a suggestion/geo pick recentres the map, firing this. Skip
        // exactly one reverse so it can't clobber the just-set preview text.
        if (skipNextReverse) { skipNextReverse = false; return; }
        if (reverseTimer) clearTimeout(reverseTimer);
        reverseTimer = setTimeout(reverseGeocodePreview, 400); // debounce ~400ms
        // NOTE: no setCoords / writeAddress here — panning never commits.
      });

      // ---------- confirm / change ----------
      if (confirmBtn) confirmBtn.addEventListener("click", function () {
        if (!previewAddress) return;
        // Commit the current centre + the shown preview address.
        enterConfirmed(previewAddress, map.getCenter());
      });
      if (changeBtn) changeBtn.addEventListener("click", function () {
        enterUnconfirmed();
        // Refresh the preview for wherever the map currently sits.
        reverseGeocodePreview();
      });

      // ---------- input -> map (preview only) ----------
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
            var coords = obj.geometry.getCoordinates();
            if (opts.keepAddress) {
              // Guard (b): preview the chosen text; skip the recentre's reverse.
              skipNextReverse = true;
              showPreview(opts.previewText || obj.getAddressLine(), coords);
            }
            map.setCenter(coords, Math.max(map.getZoom(), PLACE_ZOOM));
          },
          function () { if (msgEl) msgEl.textContent = "ℹ️ " + (T.searchErr || ""); }
        );
      }

      // Address suggestions (real Uzbek addresses). Feed the preview only.
      try {
        var suggest = new ymaps.SuggestView(addrInp, { results: 6 });
        suggest.events.add("select", function (e) {
          var val = e.get("item").value;
          geocodeAndCenter(val, { keepAddress: true, previewText: val });
        });
      } catch (e) { /* suggest is a nice-to-have; ignore if unavailable */ }

      // Enter = geocode typed text → preview (user still must confirm).
      addrInp.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          geocodeAndCenter(addrInp.value, { keepAddress: false }); // let reverse fill preview
        }
      });
      // Guard (a): if some code dispatches input during a programmatic write,
      // the forward path is a no-op.
      addrInp.addEventListener("input", function () {
        if (suppressForward) return;
      });

      // Geolocation → recenter → preview (never commits).
      if (geoBtn) geoBtn.addEventListener("click", function () {
        useGeolocation(function (lat, lng) {
          map.setCenter([lat, lng], Math.max(map.getZoom(), PLACE_ZOOM));
        });
      });

      // ---------- initial state ----------
      if (hasInitial) {
        // Edit: open directly in the confirmed state on the saved point.
        var savedAddr = (addrInp.value || "").trim();
        if (savedAddr) {
          enterConfirmed(savedAddr, [initialLat, initialLng]);
        } else {
          // Legacy row with coords but no stored address → reverse-geocode once,
          // then present as confirmed.
          ymaps.geocode([initialLat, initialLng], { results: 1 }).then(function (res) {
            var obj = res.geoObjects.get(0);
            enterConfirmed(obj ? obj.getAddressLine() : "", [initialLat, initialLng]);
          }, function () {
            enterConfirmed("", [initialLat, initialLng]);
          });
        }
      } else {
        // Create: unconfirmed, nothing committed, confirm disabled until a preview
        // exists. Do not pre-fill coords/address.
        clearCoords();
        writeAddress("");
      }

      // ---------- submit without confirming: warn, do not block ----------
      var form = wrap.closest("form");
      if (form) {
        form.addEventListener("submit", function () {
          // "no confirmed location" == hidden lat/lng empty.
          if (!latInp.value || !lngInp.value) {
            if (warnEl) warnEl.hidden = false;
          }
          // Intentionally NOT calling preventDefault — the submit proceeds.
        });
      }
    });
  }
})();
