document.addEventListener("DOMContentLoaded", function () {
  // Theme toggle
  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      document.body.classList.toggle("dark-mode");
    });
  }

  // Map elements
  const mapEl = document.getElementById("heroMap");
  const mapWrap = document.getElementById("heroMapWrap");
  const mapToggleBtn = document.getElementById("mapToggleBtn");

  if (!mapEl || typeof L === "undefined") {
    console.log("Map element or Leaflet not found");
    return;
  }

  // Prevent duplicate map init on hot reload / cached rerender
  if (mapEl._leaflet_id) {
    return;
  }

  // Create map
  const map = L.map("heroMap", {
    zoomControl: true,
    scrollWheelZoom: false,
    dragging: true,
    doubleClickZoom: true,
    touchZoom: true,
    boxZoom: false,
    keyboard: true
  }).setView([41.3111, 69.2797], 12);

  // Tiles
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);

  // Custom marker helper
  function createMarkerIcon(color, shadowColor) {
    return L.divIcon({
      className: "custom-map-marker",
      html: `
        <div style="
          width: 22px;
          height: 22px;
          background: ${color};
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          box-shadow: 0 8px 18px ${shadowColor};
          position: relative;
        ">
          <div style="
            width: 9px;
            height: 9px;
            background: #ffffff;
            border-radius: 50%;
            position: absolute;
            top: 6px;
            left: 6px;
          "></div>
        </div>
      `,
      iconSize: [22, 22],
      iconAnchor: [11, 22],
      popupAnchor: [0, -18]
    });
  }

  const blueIcon = createMarkerIcon("#2563eb", "rgba(37,99,235,0.35)");
  const redIcon = createMarkerIcon("#ff4e42", "rgba(255,78,66,0.35)");

  // Markers
  L.marker([41.3200, 69.2500], { icon: blueIcon })
    .addTo(map)
    .bindPopup(`
      <div style="font-family: Inter, sans-serif;">
        <strong>Elektrik usta</strong><br>
        <span style="color:#6b7280;">14 min</span><br>
        <span style="color:#f59e0b;font-weight:800;">★ 4.8</span>
      </div>
    `);

  L.marker([41.3050, 69.2950], { icon: blueIcon })
    .addTo(map)
    .bindPopup(`
      <div style="font-family: Inter, sans-serif;">
        <strong>Santexnik</strong><br>
        <span style="color:#6b7280;">18 min</span><br>
        <span style="color:#f59e0b;font-weight:800;">★ 4.7</span>
      </div>
    `);

  L.marker([41.3155, 69.2855], { icon: redIcon })
    .addTo(map)
    .bindPopup(`
      <div style="font-family: Inter, sans-serif;">
        <strong>Toshkent markazi</strong><br>
        <span style="color:#6b7280;">12 min</span><br>
        <span style="color:#f59e0b;font-weight:800;">★ 4.9</span>
      </div>
    `)
    .openPopup();

  L.marker([41.3000, 69.2400], { icon: blueIcon })
    .addTo(map)
    .bindPopup(`
      <div style="font-family: Inter, sans-serif;">
        <strong>Mebel yig‘ish</strong><br>
        <span style="color:#6b7280;">20 min</span><br>
        <span style="color:#f59e0b;font-weight:800;">★ 4.6</span>
      </div>
    `);

  // Expand / collapse map
  if (mapToggleBtn && mapWrap) {
    mapToggleBtn.addEventListener("click", function () {
      const isExpanded = mapWrap.classList.toggle("map-expanded");
      mapToggleBtn.textContent = isExpanded ? "Kichraytirish" : "Kattalashtirish";

      setTimeout(function () {
        map.invalidateSize();
      }, 400);
    });
  }

  // Fix initial rendering
  setTimeout(function () {
    map.invalidateSize();
  }, 500);

  // Fix map after window resize
  window.addEventListener("resize", function () {
    setTimeout(function () {
      map.invalidateSize();
    }, 200);
  });
});