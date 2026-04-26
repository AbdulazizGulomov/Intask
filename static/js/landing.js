/* ================================================================
   InTask — Landing JS
   Leaflet map with Tashkent orders, filter pills, sidebar sync,
   and tile → photo highlight interaction
   ================================================================ */

// ==================== MAP + FILTERS + SIDEBAR ====================
(function () {
  'use strict';

  // 20 real Tashkent orders covering 12 districts
  const orders = [
    { lat: 41.2829, lng: 69.2034, cat: 'plumber',    icon: '🔧', title: 'Santexnik kerak',       area: 'Chilonzor',       price: '80 000 UZS'  },
    { lat: 41.3563, lng: 69.2898, cat: 'electrician',icon: '⚡', title: "Rozetka o'rnatish",     area: 'Yunusobod',       price: '120 000 UZS' },
    { lat: 41.3259, lng: 69.3434, cat: 'cleaning',   icon: '🧽', title: 'Chuqur tozalash',       area: "Mirzo Ulug'bek",  price: '150 000 UZS' },
    { lat: 41.2916, lng: 69.2716, cat: 'ac',         icon: '❄️', title: 'Split-sistema',          area: 'Yakkasaroy',      price: '180 000 UZS' },
    { lat: 41.3250, lng: 69.2491, cat: 'repair',     icon: '🎨', title: "Devor bo'yash",         area: 'Shayxontohur',    price: '450 000 UZS' },
    { lat: 41.3376, lng: 69.2128, cat: 'plumber',    icon: '🔧', title: 'Kran almashtirish',     area: 'Olmazor',         price: '95 000 UZS'  },
    { lat: 41.2943, lng: 69.2831, cat: 'electrician',icon: '⚡', title: "Lyustra o'rnatish",     area: 'Mirobod',         price: '110 000 UZS' },
    { lat: 41.3091, lng: 69.3250, cat: 'cleaning',   icon: '🧽', title: 'Oyna tozalash',         area: 'Yashnobod',       price: '170 000 UZS' },
    { lat: 41.3156, lng: 69.1917, cat: 'ac',         icon: '❄️', title: 'Konditsioner servis',  area: 'Uchtepa',         price: '190 000 UZS' },
    { lat: 41.3263, lng: 69.2394, cat: 'repair',     icon: '🎨', title: 'Plitka yotqizish',      area: 'Chorsu',          price: '380 000 UZS' },
    { lat: 41.3111, lng: 69.2797, cat: 'plumber',    icon: '🔧', title: "Bolier ta'mir",         area: 'Amir Temur',      price: '85 000 UZS'  },
    { lat: 41.3446, lng: 69.3583, cat: 'electrician',icon: '⚡', title: "Sim o'tkazish",         area: 'TTZ',             price: '105 000 UZS' },
    { lat: 41.2410, lng: 69.2582, cat: 'cleaning',   icon: '🧽', title: 'Umumiy tozalash',       area: 'Yangihayot',      price: '140 000 UZS' },
    { lat: 41.3389, lng: 69.2283, cat: 'repair',     icon: '🎨', title: "Shift ta'miri",         area: 'Beruniy',         price: '320 000 UZS' },
    { lat: 41.3210, lng: 69.2576, cat: 'ac',         icon: '❄️', title: "Freon to'ldirish",     area: 'Hadra',           price: '200 000 UZS' },
    { lat: 41.2974, lng: 69.2700, cat: 'plumber',    icon: '🔧', title: "Unitaz o'rnatish",     area: 'Oybek',           price: '160 000 UZS' },
    { lat: 41.3087, lng: 69.2634, cat: 'electrician',icon: '⚡', title: "Shit yig'ish",          area: 'Paxtakor',        price: '115 000 UZS' },
    { lat: 41.3119, lng: 69.2700, cat: 'cleaning',   icon: '🧽', title: 'Xona tozalash',         area: 'Mustaqillik',     price: '130 000 UZS' },
    { lat: 41.3278, lng: 69.2789, cat: 'repair',     icon: '🎨', title: 'Gipskarton shift',      area: 'Darxon',          price: '400 000 UZS' },
    { lat: 41.3175, lng: 69.2900, cat: 'ac',         icon: '❄️', title: "Klimat o'rnatish",     area: 'Pushkin',         price: '175 000 UZS' }
  ];

  // Map init — guarded so page doesn't crash if Leaflet fails to load
  if (typeof L === 'undefined' || !document.getElementById('mapEl')) return;

  const map = L.map('mapEl', { zoomControl: true, scrollWheelZoom: false })
    .setView([41.3111, 69.2797], 12);

  // Avoid hijacking page scroll
  map.on('click', () => map.scrollWheelZoom.enable());
  map.on('mouseout', () => map.scrollWheelZoom.disable());

  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(map);

  const markers = [];
  orders.forEach((o, i) => {
    const pin = L.divIcon({
      html: `<div class="im-pin"><span>${o.icon}</span></div>`,
      className: '',
      iconSize: [34, 34],
      iconAnchor: [17, 34]
    });
    const m = L.marker([o.lat, o.lng], { icon: pin })
      .addTo(map)
      .bindPopup(`
        <div style="font-family:Manrope,sans-serif;min-width:170px">
          <strong style="font-size:13px;color:#0f172a">${o.icon} ${o.title}</strong><br>
          <span style="color:#64748b;font-size:12px">${o.area}</span><br>
          <span style="color:#4f6ee6;font-weight:600;font-size:13px">${o.price}</span>
        </div>`);
    m._cat = o.cat;
    m._idx = i;
    markers.push(m);
  });

  const sideList  = document.getElementById('sideList');
  const sideCount = document.getElementById('sideCount');
  const statCount = document.getElementById('statCount');

  function renderSide(list) {
    sideList.innerHTML = list.map(o => `
      <div class="order" data-idx="${o._idx}">
        <div class="order-head">
          <div class="order-ic">${o.icon}</div>
          <div class="order-title">${o.title}</div>
        </div>
        <div class="order-meta">
          <span>📍 ${o.area}</span>
          <b>${o.price}</b>
        </div>
      </div>
    `).join('');
    sideCount.textContent = list.length;
    statCount.textContent = list.length;

    sideList.querySelectorAll('.order').forEach(el => {
      el.addEventListener('click', () => {
        const idx = +el.dataset.idx;
        const o = orders[idx];
        map.flyTo([o.lat, o.lng], 15, { duration: 0.8 });
        markers[idx].openPopup();
      });
    });
  }

  renderSide(orders.map((o, i) => ({ ...o, _idx: i })));

  // Filter pills
  document.querySelectorAll('.fil').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.fil').forEach(b => b.classList.remove('on'));
      btn.classList.add('on');
      const cat = btn.dataset.cat;
      const filtered = [];
      markers.forEach((m, i) => {
        if (cat === 'all' || m._cat === cat) {
          m.addTo(map);
          filtered.push({ ...orders[i], _idx: i });
        } else {
          map.removeLayer(m);
        }
      });
      renderSide(filtered);
    });
  });
})();


// ==================== TILE → PHOTO HIGHLIGHT SYNC ====================
(function () {
  'use strict';

  // Which left-side service tile activates which right-side photo.
  // If value is null, no photo lights up (tile still highlights on its own).
  const serviceToPhoto = {
    electrician:   null,         // no photo for electrician yet
    plumber:       'plumber',
    ac:            'ac',
    cleaning:      'cleaning',
    furniture:     'furniture',
    ironing:       null,
    'deep-clean':  'cleaning',
    repair:        null
  };

  const tiles  = document.querySelectorAll('.tile[data-service]');
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