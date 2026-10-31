import base64
import re
from functools import lru_cache
from xml.sax.saxutils import escape

from bs4 import BeautifulSoup

from .client import HttpClient, UpstreamError
from .models import Achievement, GithubAchievements


class GithubAchievementsScraper:
    BASE_URL = "https://github.com/"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept": "text/html",
        "Accept-Language": "en-US,en;q=0.9",
    }
    USERNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){0,38}$", re.IGNORECASE)

    def __init__(self, client: HttpClient):
        self.client = client
        self.fetch = lru_cache(maxsize=256)(self._fetch)
        # Badge PNG URLs are content-hashed and served immutable, so caching forever is safe.
        self.fetch_image = lru_cache(maxsize=64)(self._fetch_image)

    @classmethod
    def validate_username(cls, username: str) -> str:
        name = username.strip()
        if not cls.USERNAME_RE.match(name):
            raise ValueError("username must be a valid GitHub username")
        return name

    def _fetch(self, username: str) -> GithubAchievements:
        try:
            html = self.client.get(f"{self.BASE_URL}{username}?tab=achievements", self.HEADERS)
        except UpstreamError as e:
            if e.status_code == 404:
                raise UpstreamError(404, "GitHub user not found")
            raise
        return self.parse(username, html)

    def _fetch_image(self, url: str) -> bytes:
        return self.client.get_bytes(url, self.HEADERS)

    @classmethod
    def parse(cls, username: str, html: str) -> GithubAchievements:
        soup = BeautifulSoup(html, "html.parser")
        seen: dict[str, Achievement] = {}
        # The sidebar is rendered twice (desktop + mobile layouts), so dedupe by slug.
        for img in soup.select("img.achievement-badge-sidebar"):
            link = img.find_parent("a")
            href = link.get("href", "") if link else ""
            m = re.search(r"achievement=([a-z0-9-]+)", href)
            if not m or m.group(1) in seen:
                continue
            slug = m.group(1)
            tier_el = link.select_one(".achievement-tier-label") if link else None
            tier_m = re.search(r"\d+", tier_el.get_text()) if tier_el else None
            seen[slug] = Achievement(
                slug=slug,
                name=img.get("alt", "").removeprefix("Achievement:").strip(),
                tier=int(tier_m.group()) if tier_m else 1,
                image_url=img["src"],
                url=f"{cls.BASE_URL}{username}?achievement={slug}&tab=achievements",
            )
        return GithubAchievements(username=username, count=len(seen), achievements=list(seen.values()))


class AchievementsSvgRenderer:
    ICON = 64
    GAP = 10
    FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

    def __init__(self, scraper: GithubAchievementsScraper):
        self.scraper = scraper

    def render(self, data: GithubAchievements, perline: int) -> str:
        items = data.achievements
        cols = max(1, min(perline, len(items)))
        rows = (len(items) + cols - 1) // cols if items else 1
        cell = self.ICON + self.GAP
        width = cols * cell + self.GAP
        height = rows * cell + self.GAP

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="GitHub achievements of {escape(data.username)}">'
        ]
        for i, item in enumerate(items):
            x = self.GAP + (i % cols) * cell
            y = self.GAP + (i // cols) * cell
            b64 = base64.b64encode(self.scraper.fetch_image(item.image_url)).decode("ascii")
            parts.append(
                f'<g><title>{escape(item.name)}</title>'
                f'<image x="{x}" y="{y}" width="{self.ICON}" height="{self.ICON}" '
                f'xlink:href="data:image/png;base64,{b64}"/>'
            )
            if item.tier > 1:
                parts.append(self._tier_pill(x, y, f"x{item.tier}"))
            parts.append("</g>")
        parts.append("</svg>")
        return "".join(parts)

    def _tier_pill(self, x: int, y: int, label: str) -> str:
        w, h = 10 + 7 * len(label), 18
        px, py = x + self.ICON - w + 4, y + self.ICON - h + 4
        return (
            f'<rect x="{px}" y="{py}" width="{w}" height="{h}" rx="9" fill="#f6f8fa" stroke="#d0d7de"/>'
            f'<text x="{px + w / 2}" y="{py + h / 2 + 0.5}" font-family="{self.FONT}" font-size="11" '
            f'font-weight="600" fill="#1f2328" text-anchor="middle" dominant-baseline="central">{label}</text>'
        )
