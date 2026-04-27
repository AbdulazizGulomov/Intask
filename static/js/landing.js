/* ================================================================
   InTask — Landing JS
   Leaflet map with Tashkent orders, filter pills, sidebar sync,
   and tile → photo highlight interaction
   ================================================================ */

// ==================== MAP + FILTERS + SIDEBAR ====================
(function () {
  'use strict';

  const orders = window.systemOrders || [];
  const workers = window.systemWorkers || [];

  if (typeof L === 'undefined' || !document.getElementById('mapEl')) return;

  const map = L.map('mapEl', { zoomControl: true, scrollWheelZoom: false })
    .setView([41.3111, 69.2797], 12);

  map.on('click', () => map.scrollWheelZoom.enable());
  map.on('mouseout', () => map.scrollWheelZoom.disable());

  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(map);

  let currentMode = 'orders';
  let activeCat = 'all';
  let activeMarkers = [];

  const sideList = document.getElementById('sideList');
  const sideCount = document.getElementById('sideCount');
  const statCount = document.getElementById('statCount');

  const mapModeToggle = document.getElementById('mapModeToggle');
  const mapTitle = document.getElementById('mapTitle');
  const mapActionBtn = document.getElementById('mapActionBtn');
  const lblOrders = document.getElementById('lblOrders');
  const lblWorkers = document.getElementById('lblWorkers');
  const sideTitle = document.getElementById('sideTitle');

  function renderMap() {
    activeMarkers.forEach(m => map.removeLayer(m));
    activeMarkers = [];

    let dataset = currentMode === 'orders' ? orders : workers;
    let filtered = dataset.filter(d => activeCat === 'all' || d.cat === activeCat);

    filtered.forEach((o, i) => {
      function getRC(r) {
        let v = parseFloat(r);
        if(v >= 4.8) return '#ea580c'; // Deep Orange
        if(v >= 4.6) return '#f97316'; // Orange
        if(v >= 4.3) return '#f59e0b'; // Amber
        return '#fbbf24'; // Yellow
      }
      const isWorker = currentMode === 'workers';
      const rColor = isWorker ? getRC(o.rating) : '';
      const pinHtml = isWorker 
        ? `<div class="im-pin worker-pin" style="background: ${rColor}; box-shadow: 0 4px 12px ${rColor}80; border: 2.5px solid #fff;"></div>`
        : `<div class="im-pin" style="display:flex; align-items:center; justify-content:center;"><span>${o.icon}</span></div>`;

      const pin = L.divIcon({
        html: pinHtml,
        className: '',
        iconSize: [36, 36],
        iconAnchor: [18, 36]
      });

      const popupHtml = currentMode === 'workers'
        ? `<div style="font-family:Manrope,sans-serif;min-width:170px"><strong style="font-size:14px;color:#0f172a">${o.title} <span style="color:#eab308;margin-left:4px;font-size:13px;">★ ${o.rating}</span></strong><br><span style="color:#64748b;font-size:12px">${o.service} • ${o.area}</span><br><span style="color:#4f6ee6;font-weight:600;font-size:13px">${o.price}</span></div>`
        : `<div style="font-family:Manrope,sans-serif;min-width:170px"><strong style="font-size:13px;color:#0f172a">${o.icon} ${o.title}</strong><br><span style="color:#64748b;font-size:12px">${o.area}</span><br><span style="color:#4f6ee6;font-weight:600;font-size:13px">${o.price}</span></div>`;

      const m = L.marker([o.lat, o.lng], { icon: pin })
        .addTo(map)
        .bindPopup(popupHtml);

      o._idx = i;
      m._o = o;
      activeMarkers.push(m);
    });

    sideList.innerHTML = filtered.map(o => `
      <div class="order" data-idx="${o._idx}">
        <div class="order-head">
          ${currentMode === 'workers' ? '' : `<div class="order-ic">${o.icon}</div>`}
          <div class="order-title" style="${currentMode === 'workers' ? 'display:flex; justify-content:space-between; width:100%; align-items:center;' : ''}">
            <span>${o.title}</span>
            ${currentMode === 'workers' ? `<span style="color:#eab308; font-size:13px; font-weight:600;">★ ${o.rating}</span>` : ''}
          </div>
        </div>
        <div class="order-meta">
          <span>📍 ${o.area}</span>
          <b>${o.price}</b>
        </div>
      </div>
    `).join('');

    sideCount.textContent = filtered.length;
    if (statCount) statCount.textContent = filtered.length;

    sideList.querySelectorAll('.order').forEach(el => {
      el.addEventListener('click', () => {
        const idx = +el.dataset.idx;
        map.flyTo([filtered[idx].lat, filtered[idx].lng], 15, { duration: 0.8 });
        activeMarkers[idx].openPopup();
      });
    });
  }

  renderMap();

  if (mapModeToggle) {
    mapModeToggle.addEventListener('change', (e) => {
      currentMode = e.target.checked ? 'workers' : 'orders';

      if (lblOrders) lblOrders.classList.toggle('active', currentMode === 'orders');
      if (lblWorkers) lblWorkers.classList.toggle('active', currentMode === 'workers');

      if (currentMode === 'workers') {
        if (mapTitle) mapTitle.innerHTML = 'Toshkentda yaqin ustalar';
        if (mapActionBtn) mapActionBtn.innerHTML = 'Usta qidiring →';
        if (sideTitle) sideTitle.innerHTML = 'Faol ustalar';
      } else {
        if (mapTitle) mapTitle.innerHTML = 'Toshkentda yaqin buyurtmalar';
        if (mapActionBtn) mapActionBtn.innerHTML = 'Usta sifatida qo\'shiling →';
        if (sideTitle) sideTitle.innerHTML = 'Faol buyurtmalar';
      }

      renderMap();
    });
  }

  // Filter pills
  document.querySelectorAll('.fil').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.fil').forEach(b => b.classList.remove('on'));
      btn.classList.add('on');
      activeCat = btn.dataset.cat;
      renderMap();
    });
  });
})();


// ==================== TILE → PHOTO HIGHLIGHT SYNC ====================
(function () {
  'use strict';

  // Which left-side service tile activates which right-side photo.
  // If value is null, no photo lights up (tile still highlights on its own).
  const serviceToPhoto = {
    electrician: null,         // no photo for electrician yet
    plumber: 'plumber',
    ac: 'ac',
    cleaning: 'cleaning',
    furniture: 'furniture',
    ironing: null,
    'deep-clean': 'cleaning',
    repair: null
  };

  const tiles = document.querySelectorAll('.tile[data-service]');
  const photos = document.querySelectorAll('.ph[data-photo]');
  if (!tiles.length || !photos.length) return;

  // Track how many times each tile has been clicked.
  // First click = preview (highlight). Second click on the same tile = follow the link.
  const clickCount = new WeakMap();

  tiles.forEach(tile => {
    tile.addEventListener('click', (e) => {
      const service = tile.dataset.service;
      const photoTarget = serviceToPhoto[service];
      const isActive = tile.classList.contains('is-active');

      // If this tile is already active and user clicks it again → allow the link to fire
      if (isActive) {
        return;
      }

      // First click on a fresh tile: prevent navigation, show preview
      if (tile.tagName === 'A') {
        e.preventDefault();
      }

      // Clear any previously active tile + photo
      tiles.forEach(t => t.classList.remove('is-active'));
      photos.forEach(p => p.classList.remove('is-active'));

      // Activate the clicked tile
      tile.classList.add('is-active');

      // Highlight matching photo (if one exists for this service)
      if (photoTarget) {
        const match = document.querySelector(`.ph[data-photo="${photoTarget}"]`);
        if (match) match.classList.add('is-active');
      }
    });
  });

  // Click a photo on the right → activate the matching tile on the left
  photos.forEach(photo => {
    photo.addEventListener('click', () => {
      const photoKey = photo.dataset.photo;
      // Find which service tile maps to this photo
      const serviceKey = Object.keys(serviceToPhoto).find(
        k => serviceToPhoto[k] === photoKey
      );
      if (!serviceKey) return;

      const tile = document.querySelector(`.tile[data-service="${serviceKey}"]`);
      if (!tile) return;

      // If tile is already active, ignore the photo click (prevents accidental nav)
      if (tile.classList.contains('is-active')) {
        tiles.forEach(t => t.classList.remove('is-active'));
        photos.forEach(p => p.classList.remove('is-active'));
        return;
      }

      // Otherwise, simulate a preview click on the tile
      tiles.forEach(t => t.classList.remove('is-active'));
      photos.forEach(p => p.classList.remove('is-active'));
      tile.classList.add('is-active');
      photo.classList.add('is-active');
    });
  });

  // Clicking anywhere outside the picker or collage clears the active state
  document.addEventListener('click', (e) => {
    if (e.target.closest('.picker') || e.target.closest('.hero-r')) return;
    tiles.forEach(t => t.classList.remove('is-active'));
    photos.forEach(p => p.classList.remove('is-active'));
  });
})();