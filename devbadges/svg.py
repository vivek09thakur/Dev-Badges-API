import base64
import io
import textwrap
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import NamedTuple, Optional
from xml.sax.saxutils import escape, quoteattr

from PIL import Image

from .client import HttpClient
from .constants import (
    BROWSER_HEADERS,
    CACHE_SIZE,
    FONT,
    GAP,
    ICON_WORKERS,
    MAX_ASPECT,
    NOTICE_CHAR_WIDTH,
    NOTICE_FONT_SIZE,
    NOTICE_LINE_HEIGHT,
    NOTICE_WRAP,
    PAD,
    RADIUS,
    TEXT_FILL,
    TILE,
    TILE_FILL,
    Theme,
)


class GridItem(NamedTuple):
    image_url: str
    title: str
    label: Optional[str] = None


class Icon(NamedTuple):
    data_uri: str
    width: int
    card: bool


class BadgeGridRenderer:
    def __init__(self, client: HttpClient):
        self.client = client
        self.icon = lru_cache(maxsize=CACHE_SIZE)(self._icon)

    def _icon(self, url: str) -> Icon:
        img = Image.open(io.BytesIO(self.client.get_bytes(url, BROWSER_HEADERS))).convert("RGBA")
        img = img.crop(img.getchannel("A").getbbox() or (0, 0, *img.size))
        w, h = img.size
        # Opaque corners = artwork is a card that should fill its tile; transparent = icon that sits on a tile
        card = all(img.getpixel(p)[3] >= 250 for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)))
        aspect = min(max(w / h, 1 / MAX_ASPECT), MAX_ASPECT)
        img.thumbnail((2 * TILE * MAX_ASPECT, 2 * TILE), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        data_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        return Icon(data_uri, round(TILE * aspect), card)

    @staticmethod
    def _open(width: int, height: int, aria_label: str) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label={quoteattr(aria_label)}>'
        )

    def render(self, items: list[GridItem], perline: int, aria_label: str, theme: Theme = "dark") -> str:
        fill = TILE_FILL[theme]
        with ThreadPoolExecutor(max_workers=ICON_WORKERS) as pool:
            icons = list(pool.map(self.icon, [item.image_url for item in items]))
        tiles = list(zip(items, icons))
        rows = [tiles[i : i + perline] for i in range(0, len(tiles), perline)]
        row_h = TILE + GAP
        width = GAP + max((sum(icon.width + GAP for _, icon in row) for row in rows), default=row_h)
        height = GAP + max(len(rows), 1) * row_h
        parts = [self._open(width, height, aria_label)]
        card_widths = sorted({icon.width for icon in icons if icon.card})
        if card_widths:
            parts.append("<defs>")
            for w in card_widths:
                parts.append(f'<clipPath id="c{w}"><rect width="{w}" height="{TILE}" rx="{RADIUS}"/></clipPath>')
            parts.append("</defs>")
        for r, row in enumerate(rows):
            x, y = GAP, GAP + r * row_h
            for item, icon in row:
                parts.append(f'<g transform="translate({x} {y})"><title>{escape(item.title)}</title>')
                parts.append(self._tile(icon, fill))
                if item.label:
                    parts.append(self._pill(icon.width, item.label))
                parts.append("</g>")
                x += icon.width + GAP
        parts.append("</svg>")
        return "".join(parts)

    def notice(self, text: str, theme: Theme = "dark") -> str:
        """A single tile carrying a message, for when there is nothing else an <img> embed could show."""
        lines = textwrap.wrap(text, NOTICE_WRAP)
        inset = 2 * PAD
        w = 2 * inset + NOTICE_CHAR_WIDTH * max(len(line) for line in lines)
        h = 2 * PAD + NOTICE_LINE_HEIGHT * len(lines)
        parts = [
            self._open(w + 2 * GAP, h + 2 * GAP, text),
            f'<g transform="translate({GAP} {GAP})"><rect width="{w}" height="{h}" rx="{RADIUS}" fill="{TILE_FILL[theme]}"/>',
        ]
        for i, line in enumerate(lines):
            parts.append(
                f'<text x="{inset}" y="{PAD + NOTICE_LINE_HEIGHT * (i + 0.5)}" font-family="{FONT}" '
                f'font-size="{NOTICE_FONT_SIZE}" fill="{TEXT_FILL[theme]}" dominant-baseline="central">'
                f"{escape(line)}</text>"
            )
        parts.append("</g></svg>")
        return "".join(parts)

    def _tile(self, icon: Icon, fill: str) -> str:
        w, h = icon.width, TILE
        if icon.card:
            return (
                f'<image width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice" '
                f'clip-path="url(#c{w})" xlink:href="{icon.data_uri}"/>'
                f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{RADIUS - 0.5}" '
                f'fill="none" stroke="#000" stroke-opacity=".12"/>'
            )
        return (
            f'<rect width="{w}" height="{h}" rx="{RADIUS}" fill="{fill}"/>'
            f'<image x="{PAD}" y="{PAD}" width="{w - 2 * PAD}" height="{h - 2 * PAD}" '
            f'preserveAspectRatio="xMidYMid meet" xlink:href="{icon.data_uri}"/>'
        )

    def _pill(self, tile_w: int, label: str) -> str:
        w, h = 10 + 7 * len(label), 18
        px, py = tile_w - w - 3, TILE - h - 3
        return (
            f'<rect x="{px}" y="{py}" width="{w}" height="{h}" rx="9" fill="#f6f8fa" stroke="#d0d7de"/>'
            f'<text x="{px + w / 2}" y="{py + h / 2 + 0.5}" font-family="{FONT}" font-size="11" '
            f'font-weight="600" fill="#1f2328" text-anchor="middle" dominant-baseline="central">'
            f"{escape(label)}</text>"
        )
