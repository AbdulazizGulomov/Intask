import os
import re

html_path = 'templates/landing.html'
js_path = 'static/js/landing.js'

with open(html_path, 'r') as f:
    html = f.read()

def process_worker(match):
    rating_str = match.group(2)
    rating = float(rating_str)
    
    # Base calculation formula:
    # 4.0 returns 100,000 
    # 5.0 returns 500,000
    price = int((rating - 4.0) * 400000 + 100000)
    
    # Snap variables elegantly to strict rounding
    price = round(price / 10000) * 10000
    
    # Re-assemble formatted currency text spacing
    price_str = f"{price:,}".replace(",", " ")
    
    full_str = match.group(1)
    # Inject mapped token natively maintaining template string
    full_str = re.sub(r'price:\s*`[\d\s]+', f'price: `{price_str} ', full_str)
    return full_str

new_html = re.sub(r"(\{[^}]*?rating:\s*'([\d.]+)'.*?price:\s*`[\d\s]+.*?\})", process_worker, html)
new_html = new_html.replace('?v=5', '?v=6')

with open(html_path, 'w') as f:
    f.write(new_html)

with open(js_path, 'r') as f:
    js = f.read()

# Erase the raw numeric value pushing pure geometric aesthetics on markers
js = re.sub(
    r'<div class="im-pin worker-pin"[^>]*>\$\{o\.rating\}</div>',
    r'<div class="im-pin worker-pin" style="width: 22px; height: 22px; background: ${rColor}; box-shadow: 0 4px 12px ${rColor}80; border: 3px solid #fff; border-radius: 50%; box-sizing: border-box; display: inline-block;"></div>',
    js
)

with open(js_path, 'w') as f:
    f.write(js)

print("Pricing aligned dynamically and empty gradient dots implemented.")
