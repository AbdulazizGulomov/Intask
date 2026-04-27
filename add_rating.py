import re
import random

# Read HTML
with open('templates/landing.html', 'r') as f:
    html = f.read()

# Inject rating property and star icon
def inject_rating(match):
    r = round(random.uniform(4.5, 5.0), 1)
    return f"icon: '⭐', rating: '{r}', title: "

new_html = re.sub(r"icon:\s*'',\s*title:\s*", inject_rating, html)
new_html = new_html.replace('?v=3', '?v=4')

with open('templates/landing.html', 'w') as f:
    f.write(new_html)

# Read JS
with open('static/js/landing.js', 'r') as f:
    js = f.read()

# 1. Restore map pin icon rendering for workers
js = js.replace('''<span>${currentMode === 'workers' ? '' : o.icon}</span>''', '''<span>${o.icon}</span>''')

# 2. Add rating to Popup
target_popup = '''<strong style="font-size:14px;color:#0f172a">${o.title}</strong>'''
replacement_popup = '''<strong style="font-size:14px;color:#0f172a">${o.title} <span style="color:#eab308;margin-left:4px;font-size:13px;">★ ${o.rating}</span></strong>'''
js = js.replace(target_popup, replacement_popup)

# 3. Add rating to sidelist and flex styling
target_sidelist = '''          ${currentMode === 'workers' ? '' : `<div class="order-ic">${o.icon}</div>`}
          <div class="order-title">${o.title}</div>'''

replacement_sidelist = '''          ${currentMode === 'workers' ? '' : `<div class="order-ic">${o.icon}</div>`}
          <div class="order-title" style="${currentMode === 'workers' ? 'display:flex; justify-content:space-between; width:100%; align-items:center;' : ''}">
            <span>${o.title}</span>
            ${currentMode === 'workers' ? `<span style="color:#eab308; font-size:13px; font-weight:600;">★ ${o.rating}</span>` : ''}
          </div>'''
js = js.replace(target_sidelist, replacement_sidelist)

with open('static/js/landing.js', 'w') as f:
    f.write(js)

print("Ratings seamlessly integrated into JS DOM renderer.")
