"""
Generate all InTask brand assets from the master logo.

Source : static/img/intasklogo.png  (600x600, transparent, full lockup:
         tri-color ribbon mark above the "In Task" wordmark)
Output : static/img/brand/*   (re-run any time; deterministic)

All resizing uses LANCZOS. Run from the project root:

    python scripts/make_brand_assets.py
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "static", "img", "intasklogo.png")
OUT = os.path.join(ROOT, "static", "img", "brand")
os.makedirs(OUT, exist_ok=True)

WHITE = (255, 255, 255, 255)
ALPHA_THRESHOLD = 16  # anything more opaque than this counts as "content"


def content_rows(im):
    """Return list of y-rows that contain at least one opaque pixel."""
    a = im.split()[3]
    W, H = im.size
    px = a.load()
    rows = []
    for y in range(H):
        for x in range(W):
            if px[x, y] > ALPHA_THRESHOLD:
                rows.append(y)
                break
    return rows


def opaque_bands(im):
    """Contiguous (y0, y1) bands of rows that contain opaque pixels."""
    rows = set(content_rows(im))
    bands, start, prev = [], None, None
    for y in sorted(rows):
        if start is None:
            start = prev = y
        elif y == prev + 1:
            prev = y
        else:
            bands.append((start, prev))
            start = prev = y
    if start is not None:
        bands.append((start, prev))
    return bands


def trim(im):
    """Crop transparent padding to the tight content bbox."""
    return im.crop(im.getbbox())


def fit_height(im, target_h):
    """Resize preserving aspect ratio so the height == target_h."""
    w, h = im.size
    target_w = max(1, round(w * target_h / h))
    return im.resize((target_w, target_h), Image.LANCZOS)


def square_canvas(im, size, pad_ratio, bg=None):
    """Center `im` (already trimmed) on a `size`x`size` canvas, scaled so the
    longest side occupies (1 - 2*pad_ratio) of the canvas. bg=None -> transparent."""
    inner = round(size * (1 - 2 * pad_ratio))
    w, h = im.size
    scale = inner / max(w, h)
    new = im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), bg if bg else (0, 0, 0, 0))
    ox = (size - new.width) // 2
    oy = (size - new.height) // 2
    canvas.paste(new, (ox, oy), new)
    return canvas


def brand_blue(im):
    """Mean RGB of the strongly-blue pixels in the mark -> representative hex."""
    im = im.convert("RGBA")
    px = im.load()
    W, H = im.size
    r_sum = g_sum = b_sum = n = 0
    for y in range(0, H):
        for x in range(0, W):
            r, g, b, a = px[x, y]
            if a > 200 and b > 100 and b > r + 30 and b > g + 20:
                r_sum += r; g_sum += g; b_sum += b; n += 1
    if not n:
        return "#0C549C"
    return "#%02X%02X%02X" % (round(r_sum / n), round(g_sum / n), round(b_sum / n))


def save(im, name, quantize=False, **kw):
    # Full-lockup PNGs carry smooth tri-color gradients that balloon past the
    # 150 KB budget as RGBA; FASTOCTREE keeps the alpha channel while shrinking
    # them ~5x with no visible loss at these sizes.
    if quantize:
        im = im.quantize(colors=256, method=Image.FASTOCTREE)
    path = os.path.join(OUT, name)
    im.save(path, **kw)
    size = os.path.getsize(path)
    flag = "  <-- OVER 150KB!" if size > 150 * 1024 else ""
    print(f"  {name:22s} {im.size[0]:>4}x{im.size[1]:<4} {size/1024:7.1f} KB{flag}")
    return size


def main():
    master = Image.open(SRC).convert("RGBA")
    print(f"source: {SRC}  {master.size}  {master.mode}")

    # --- Split mark from wordmark using the transparent gap between bands ---
    bands = opaque_bands(master)
    print("opaque bands (y0,y1):", bands)
    mark_band = bands[0]                      # top band = ribbon mark
    mark_region = master.crop((0, mark_band[0], master.width, mark_band[1] + 1))
    mark_tight = trim(mark_region)            # tight ribbon mark
    full_tight = trim(master)                 # tight full lockup

    print("generated assets -> static/img/brand/")

    # 1-2. Full lockup at 320px and 640px tall (transparent, palette-quantized)
    save(fit_height(full_tight, 320), "logo-full.png", quantize=True, optimize=True)
    save(fit_height(full_tight, 640), "logo-full@2x.png", quantize=True, optimize=True)

    # 3. Mark only, 512x512, transparent, centered, small even padding
    mark512 = square_canvas(mark_tight, 512, pad_ratio=0.08)
    save(mark512, "logo-mark.png", optimize=True)

    # 4. Mark on solid white, 512x512
    mark512_white = square_canvas(mark_tight, 512, pad_ratio=0.08, bg=WHITE)
    save(mark512_white.convert("RGB"), "logo-mark-white.png", optimize=True)

    # 5. favicon.ico (multi-size 16/32/48) from the mark
    ico = os.path.join(OUT, "favicon.ico")
    mark512.save(ico, sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"  {'favicon.ico':22s} 16/32/48  {os.path.getsize(ico)/1024:7.1f} KB")

    # 6. PNG favicons from the mark
    for px in (32, 192, 512):
        save(mark512.resize((px, px), Image.LANCZOS), f"favicon-{px}.png", optimize=True)

    # 7. apple-touch-icon 180x180 on SOLID WHITE (iOS ignores alpha)
    apple = square_canvas(mark_tight, 180, pad_ratio=0.12, bg=WHITE).convert("RGB")
    save(apple, "apple-touch-icon.png", optimize=True)

    # 8. og-image 1200x630, full lockup centered on solid white
    og = Image.new("RGB", (1200, 630), (255, 255, 255))
    lockup = fit_height(full_tight, 380)
    og.paste(lockup, ((1200 - lockup.width) // 2, (630 - lockup.height) // 2), lockup)
    save(og, "og-image.png", optimize=True)

    print("theme_color (brand blue):", brand_blue(mark_tight))


if __name__ == "__main__":
    main()