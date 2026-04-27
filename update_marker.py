import os
import re
import random

# PATCH HTML
with open('templates/landing.html', 'r') as f:
    html = f.read()

# Make sure to keep consistent randomization sequence between reruns to avoid volatile state bouncing.
# However, user requests purely random between 4 and 5.
def update_rating(match):
    r = round(random.uniform(4.1, 5.0), 1)
    if r > 5.0: r = 5.0
    # Clean the icon param completely to make way for numerical markers exclusively
    return f"icon: '', rating: '{r}', title: "

# Swap existing injected markers
html = re.sub(r"icon:\s*'[^']*',\s*rating:\s*'[\d.]+',\s*title:\s*", update_rating, html)
# Catch uninitialized ones
html = re.sub(r"icon:\s*'',\s*title:\s*", update_rating, html)

# Bust cache
html = html.replace('?v=4', '?v=5')

# Commit HTML
with open('templates/landing.html', 'w') as f:
    f.write(html)


# PATCH JS
with open('static/js/landing.js', 'r') as f:
    js = f.read()

target_marker = '''      const pinClassName = currentMode === 'workers' ? 'im-pin worker-pin' : 'im-pin';
      const pin = L.divIcon({
        html: `<div class="${pinClassName}" style="${currentMode === 'workers' ? 'background:var(--accent-1); color:#fff;' : ''}"><span>${o.icon}</span></div>`,
        className: '',
        iconSize: [34, 34],
        iconAnchor: [17, 34]
      });'''

replacement_marker = '''      function getRC(r) {
        let v = parseFloat(r);
        if(v >= 4.8) return '#ea580c'; // Deep Orange
        if(v >= 4.6) return '#f97316'; // Orange
        if(v >= 4.3) return '#f59e0b'; // Amber
        return '#fbbf24'; // Yellow
      }
      const isWorker = currentMode === 'workers';
      const rColor = isWorker ? getRC(o.rating) : '';
      const pinHtml = isWorker 
        ? `<div class="im-pin worker-pin" style="background: ${rColor}; color: #fff; font-weight:700; font-size:13px; box-shadow: 0 4px 12px ${rColor}60; display:flex; align-items:center; justify-content:center; border: 2px solid #fff;">${o.rating}</div>`
        : `<div class="im-pin" style="display:flex; align-items:center; justify-content:center;"><span>${o.icon}</span></div>`;

      const pin = L.divIcon({
        html: pinHtml,
        className: '',
        iconSize: [36, 36],
        iconAnchor: [18, 36]
      });'''

if 'getRC(r)' not in js:
    js = js.replace(target_marker, replacement_marker)

# Ensure popup rating doesn't have the explicit star anymore since we removed stars everywhere?
# User said: "ushbu map ichidagi shu qismdagi yulduzchani olib tashlaysan... u yerga hech qanday ikonka kerak emas".
# They might mean *specifically* inside the transparent map marker element itself. 
# But just in case, I am keeping POPUP side star or removing? "reyting korsatib tursin yulduzcha yonida reyting raqamo".
# They asked to *keep* star next to rating number elsewhere ("yulduzcha yonida reyting raqamo"), but remove from map!

with open('static/js/landing.js', 'w') as f:
    f.write(js)

print("Dynamic rating gradient logic executed.")
