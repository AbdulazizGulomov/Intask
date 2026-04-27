import os
import re

html_path = 'templates/landing.html'
with open(html_path, 'r') as f:
    content = f.read()

# Fix literal rendering issues by migrating to blocktrans for phrases containing single quotes
content = content.replace('{% trans "Siz ham" %} <em>{% trans "usta bo\'ling" %}</em>', '{% blocktrans %}Siz ham{% endblocktrans %} <em>{% blocktrans %}usta bo\'ling{% endblocktrans %}</em>')
content = content.replace('{% trans "va 15 mln so\'mgacha toping" %}', '{% blocktrans %}va 15 mln so\'mgacha toping{% endblocktrans %}')
content = content.replace('{% trans "InTask\'da buyurtmalar oling, mijozlar bilan ishlang va daromadingizni oshiring. Ro\'yxatdan o\'tish bepul." %}', '{% blocktrans %}InTask\'da buyurtmalar oling, mijozlar bilan ishlang va daromadingizni oshiring. Ro\'yxatdan o\'tish bepul.{% endblocktrans %}')

# Safely inject translated currency nodes
content = re.sub(r"price: '(\d+ 000) UZS'", r"price: `\1 {% trans \"UZS\" %}`", content)
content = re.sub(r"price: '(\d+ 000) UZS/soat'", r"price: `\1 {% trans \"UZS\" %}/{% trans \"soat\" %}`", content)

with open(html_path, 'w') as f:
    f.write(content)

css_path = 'static/css/landing.css'
with open(css_path, 'r') as f:
    css_content = f.read()

styles = """
/* Elevated Typography Styles */
.trust-num {
  font-size: 26px !important;
  font-weight: 700 !important;
  color: var(--accent) !important;
  letter-spacing: -0.01em;
}

.cta-stat b.count-up {
  font-size: 32px !important;
  font-weight: 800 !important;
  color: var(--accent) !important;
}

.cta-earn-text strong {
  font-size: 30px !important;
  font-weight: 800 !important;
  color: var(--accent) !important;
}
"""
if "Elevated Typography Styles" not in css_content:
    with open(css_path, 'a') as f:
        f.write(styles)

# Open translate_all.py to append 'UZS'
trans_path = 'translate_all.py'
with open(trans_path, 'r') as f:
    trans_content = f.read()

trans_content = trans_content.replace('"Chuqur tozalash": "Глубокая уборка"', '"Chuqur tozalash": "Глубокая уборка",\n    "UZS": "сум"')
trans_content = trans_content.replace('"Chuqur tozalash": "Deep cleaning"', '"Chuqur tozalash": "Deep cleaning",\n    "UZS": "UZS"')

with open(trans_path, 'w') as f:
    f.write(trans_content)

print("Deploy structural patches successful.")
