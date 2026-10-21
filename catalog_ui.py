from __future__ import annotations

import html
import re
import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


PALETTE = {
    "Black": "#171717", "White": "#f7f7f2", "Blue": "#5578a8",
    "Beige": "#cdbb9c", "Grey": "#8b9298", "Red": "#a94d4d",
    "Green": "#718b70", "Yellow": "#c8a84d", "Pink": "#c98ca0",
}


def family(value: str) -> str:
    text = value.lower()
    if any(x in text for x in ("t-shirt", "tee", "top", "shirt", "blouse")):
        return "T-shirts & tops"
    if any(x in text for x in ("trouser", "pants", "jeans", "shorts", "skirt")):
        return "Trousers & bottoms"
    if any(x in text for x in ("dress", "jumpsuit")):
        return "Dresses"
    if any(x in text for x in ("jacket", "coat", "blazer", "cardigan", "hoodie")):
        return "Jackets & layers"
    if any(x in text for x in ("shoe", "boot", "sandal", "sneaker")):
        return "Shoes"
    if any(x in text for x in ("bag", "belt", "scarf", "hat", "accessor")):
        return "Accessories"
    return "All"


def _shape(product_type: str) -> str:
    text = product_type.lower()
    if any(x in text for x in ("trouser", "pants", "jeans", "shorts")):
        return '<path d="M88 54h45l-4 100-17 2-5-60-7 60-18-2z"/>'
    if any(x in text for x in ("dress", "skirt")):
        return '<path d="M93 48h34l8 48 28 57H57l28-57z"/>'
    if any(x in text for x in ("jacket", "coat", "hoodie", "cardigan")):
        return '<path d="M91 48h38l28 25-15 20-10-8 4 71H84l4-71-10 8-15-20z"/>'
    if any(x in text for x in ("shoe", "boot", "sandal")):
        return '<path d="M66 117l54 8 42 20v13H59c-5-14-1-29 7-41z"/>'
    return '<path d="M92 48h36l30 25-15 22-14-11v71H91V84L77 95 62 73z"/>'


def product_svg(article: Any) -> str:
    colour = getattr(article, "colour_group", "Black") or "Black"
    fill = PALETTE.get(str(colour), "#4c5965")
    label = html.escape(str(getattr(article, "product_type", "Fashion item")))
    return f'''<svg viewBox="0 0 220 220" role="img" aria-label="{label}">
      <defs><linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
        <stop stop-color="#f8f4ee"/><stop offset="1" stop-color="#e8dfd3"/></linearGradient>
      </defs><rect width="220" height="220" rx="18" fill="url(#bg)"/>
      <circle cx="180" cy="38" r="28" fill="#ffffff" opacity=".55"/>
      <g fill="{fill}" stroke="#242424" stroke-width="2" stroke-linejoin="round">{_shape(label)}</g>
      <text x="16" y="198" font-family="Arial" font-size="13" fill="#292929">{label[:23]}</text>
    </svg>'''


def product_image_bytes(article: Any) -> bytes:
    """Return the generated product art as native image bytes.

    Streamlit's native image renderer is more reliable than embedding a
    base64 data URI inside st.html, especially on Windows browsers.
    """
    return product_svg(article).encode("utf-8")


def product_png_bytes(article: Any) -> bytes:
    """Render product art as PNG for browsers that block inline SVG images."""
    colour = getattr(article, "colour_group", "Black") or "Black"
    fill = PALETTE.get(str(colour), "#4c5965")
    image = Image.new("RGB", (440, 440), "#eee8de")
    draw = ImageDraw.Draw(image)
    draw.ellipse((300, 30, 410, 140), fill="#ffffff")
    text = str(getattr(article, "product_type", "Fashion item"))[:26]
    low = text.lower()
    if any(x in low for x in ("trouser", "pants", "jeans", "shorts")):
        points = [(176,108),(266,108),(258,308),(224,312),(214,192),(200,312),(164,308)]
    elif any(x in low for x in ("dress", "skirt")):
        points = [(186,96),(254,96),(270,192),(326,314),(114,314),(170,192)]
    elif any(x in low for x in ("shoe", "boot", "sandal")):
        points = [(120,250),(230,266),(316,306),(326,332),(104,332),(90,298)]
    else:
        points = [(184,96),(256,96),(316,146),(282,190),(258,168),(258,314),(182,314),(182,168),(158,190),(124,146)]
    draw.polygon(points, fill=fill, outline="#242424", width=4)
    draw.text((28, 386), text, fill="#292929")
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


ASSET_FILES = {
    "T-shirts & tops": "tshirts/tee.svg",
    "Trousers & bottoms": "trousers/trousers.svg",
    "Dresses": "dresses/dress.svg",
    "Jackets & layers": "jackets/jacket.svg",
    "Shoes": "shoes/shoes.svg",
    "Accessories": "accessories/accessories.svg",
}


ASSET_ROOT = Path("D:/gt/user_app/assets")
PRODUCT_IMAGE_ROOT = Path("D:/gt/cache/catalog_images")


def product_image_path(article: Any) -> Path:
    """Materialize one deterministic local SVG for Streamlit's media server."""
    article_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(getattr(article, "article_id", "fashion-item")))
    path = PRODUCT_IMAGE_ROOT / f"{article_id}.svg"
    if not path.exists():
        PRODUCT_IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
        path.write_text(product_svg(article), encoding="utf-8")
    return path


def category_image_path(category: str) -> Path:
    relative = ASSET_FILES.get(category, "banners/new-season.svg")
    path = ASSET_ROOT / relative
    return path if path.exists() else ASSET_ROOT / "banners/new-season.svg"


def category_image_html(category: str) -> str:
    """Backward-compatible HTML helper for non-Streamlit callers."""
    path = category_image_path(category)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def clean_title(article: Any) -> str:
    name = str(getattr(article, "name", "Fashion item") or "Fashion item")
    return re.sub(r"\s+", " ", name).strip()[:56]
