import os
import re

html_path = 'templates/landing.html'
js_path = 'static/js/landing.js'

with open(html_path, 'r') as f:
    html = f.read()

def process_worker(match):
    rating_str = match.group(2)
    rating = float(rating_str)
    
    # Downscale prices based on realistic local economy for generic services
    # 4.0 returns 50,000 
    # 5.0 returns 200,000
    price = int((rating - 4.0) * 150000 + 50000)
    
    # 10k rounding
    price = round(price / 10000) * 10000
    
    price_str = f"{price:,}".replace(",", " ")
    
    full_str = match.group(1)
    full_str = re.sub(r'price:\s*`[\d\s]+', f'price: `{price_str} ', full_str)
    return full_str

new_html = re.sub(r"(\{[^}]*?rating:\s*'([\d.]+)'.*?price:\s*`[\d\s]+.*?\})", process_worker, html)
new_html = new_html.replace('?v=6', '?v=7')

with open(html_path, 'w') as f:
    f.write(new_html)

with open(js_path, 'r') as f:
    js = f.read()

# Safely extract explicitly circular constraints injected previously
target_style = 'style="width: 22px; height: 22px; background: ${rColor}; box-shadow: 0 4px 12px ${rColor}80; border: 3px solid #fff; border-radius: 50%; box-sizing: border-box; display: inline-block;"'
replacement_style = 'style="background: ${rColor}; box-shadow: 0 4px 12px ${rColor}80; border: 2.5px solid #fff;"'

js = js.replace(target_style, replacement_style)

with open(js_path, 'w') as f:
    f.write(js)

print("Pricing algorithm downgraded and teardrops restored.")
