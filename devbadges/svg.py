import base64
import io
from functools import lru_cache
from typing import NamedTuple, Optional
from xml.sax.saxutils import escape, quoteattr

from PIL import Image

from .client import BROWSER_HEADERS, HttpClient


class GridItem(NamedTuple):
    image_url: str
    title: str
    label: Optional[str] = None


class BadgeGridRenderer:
    ICON = 64
    GAP = 10
    ICON_PX = ICON * 2
    FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

    def __init__(self, client: HttpClient):
        self.client = client
        self.icon_data_uri = lru_cache(maxsize=256)(self._icon_data_uri)

    def _icon_data_uri(self, url: str) -> str:
        img = Image.open(io.BytesIO(self.client.get_bytes(url, BROWSER_HEADERS)))
        img.thumbnail((self.ICON_PX, self.ICON_PX), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.convert("RGBA").save(buf, format="PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    def render(self, items: list[GridItem], perline: int, aria_label: str) -> str:
        cols = max(1, min(perline, len(items)))
        rows = (len(items) + cols - 1) // cols if items else 1
        cell = self.ICON + self.GAP
        width = cols * cell + self.GAP
        height = rows * cell + self.GAP
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label={quoteattr(aria_label)}>'
        ]
        for i, item in enumerate(items):
            x = self.GAP + (i % cols) * cell
            y = self.GAP + (i // cols) * cell
            parts.append(
                f"<g><title>{escape(item.title)}</title>"
                f'<image x="{x}" y="{y}" width="{self.ICON}" height="{self.ICON}" '
                f'preserveAspectRatio="xMidYMid meet" xlink:href="{self.icon_data_uri(item.image_url)}"/>'
            )
            if item.label:
                parts.append(self._pill(x, y, item.label))
            parts.append("</g>")
        parts.append("</svg>")
        return "".join(parts)

    def _pill(self, x: int, y: int, label: str) -> str:
        w, h = 10 + 7 * len(label), 18
        px, py = x + self.ICON - w + 4, y + self.ICON - h + 4
        return (
            f'<rect x="{px}" y="{py}" width="{w}" height="{h}" rx="9" fill="#f6f8fa" stroke="#d0d7de"/>'
            f'<text x="{px + w / 2}" y="{py + h / 2 + 0.5}" font-family="{self.FONT}" font-size="11" '
            f'font-weight="600" fill="#1f2328" text-anchor="middle" dominant-baseline="central">'
            f"{escape(label)}</text>"
        )
