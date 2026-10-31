import base64
import io
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import NamedTuple, Optional
from xml.sax.saxutils import escape, quoteattr

from PIL import Image

from .client import BROWSER_HEADERS, HttpClient


class GridItem(NamedTuple):
    image_url: str
    title: str
    label: Optional[str] = None


class Icon(NamedTuple):
    data_uri: str
    width: int
    card: bool


class BadgeGridRenderer:
    TILE = 64
    PAD = 8
    GAP = 10
    RADIUS = 15
    MAX_ASPECT = 2
    # Same tile colours skillicons.dev uses
    THEMES = {"dark": "#242938", "light": "#F4F2ED"}
    FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

    def __init__(self, client: HttpClient):
        self.client = client
        self.icon = lru_cache(maxsize=256)(self._icon)

    def _icon(self, url: str) -> Icon:
        img = Image.open(io.BytesIO(self.client.get_bytes(url, BROWSER_HEADERS))).convert("RGBA")
        img = img.crop(img.getchannel("A").getbbox() or (0, 0, *img.size))
        w, h = img.size
        # Opaque corners = artwork is a card that should fill its tile; transparent = icon that sits on a tile
        card = all(img.getpixel(p)[3] >= 250 for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)))
        aspect = min(max(w / h, 1 / self.MAX_ASPECT), self.MAX_ASPECT)
        img.thumbnail((2 * self.TILE * self.MAX_ASPECT, 2 * self.TILE), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        data_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        return Icon(data_uri, round(self.TILE * aspect), card)

    def render(self, items: list[GridItem], perline: int, aria_label: str, theme: str = "dark") -> str:
        fill = self.THEMES[theme]
        with ThreadPoolExecutor(max_workers=8) as pool:
            icons = list(pool.map(self.icon, [item.image_url for item in items]))
        tiles = list(zip(items, icons))
        rows = [tiles[i : i + perline] for i in range(0, len(tiles), perline)]
        row_h = self.TILE + self.GAP
        width = self.GAP + max((sum(icon.width + self.GAP for _, icon in row) for row in rows), default=row_h)
        height = self.GAP + max(len(rows), 1) * row_h
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label={quoteattr(aria_label)}>'
        ]
        card_widths = sorted({icon.width for icon in icons if icon.card})
        if card_widths:
            parts.append("<defs>")
            for w in card_widths:
                parts.append(f'<clipPath id="c{w}"><rect width="{w}" height="{self.TILE}" rx="{self.RADIUS}"/></clipPath>')
            parts.append("</defs>")
        for r, row in enumerate(rows):
            x, y = self.GAP, self.GAP + r * row_h
            for item, icon in row:
                parts.append(f'<g transform="translate({x} {y})"><title>{escape(item.title)}</title>')
                parts.append(self._tile(icon, fill))
                if item.label:
                    parts.append(self._pill(icon.width, item.label))
                parts.append("</g>")
                x += icon.width + self.GAP
        parts.append("</svg>")
        return "".join(parts)

    def _tile(self, icon: Icon, fill: str) -> str:
        w, h = icon.width, self.TILE
        if icon.card:
            return (
                f'<image width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice" '
                f'clip-path="url(#c{w})" xlink:href="{icon.data_uri}"/>'
                f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{self.RADIUS - 0.5}" '
                f'fill="none" stroke="#000" stroke-opacity=".12"/>'
            )
        return (
            f'<rect width="{w}" height="{h}" rx="{self.RADIUS}" fill="{fill}"/>'
            f'<image x="{self.PAD}" y="{self.PAD}" width="{w - 2 * self.PAD}" height="{h - 2 * self.PAD}" '
            f'preserveAspectRatio="xMidYMid meet" xlink:href="{icon.data_uri}"/>'
        )

    def _pill(self, tile_w: int, label: str) -> str:
        w, h = 10 + 7 * len(label), 18
        px, py = tile_w - w - 3, self.TILE - h - 3
        return (
            f'<rect x="{px}" y="{py}" width="{w}" height="{h}" rx="9" fill="#f6f8fa" stroke="#d0d7de"/>'
            f'<text x="{px + w / 2}" y="{py + h / 2 + 0.5}" font-family="{self.FONT}" font-size="11" '
            f'font-weight="600" fill="#1f2328" text-anchor="middle" dominant-baseline="central">'
            f"{escape(label)}</text>"
        )
