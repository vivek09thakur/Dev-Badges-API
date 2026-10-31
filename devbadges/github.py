import re
from functools import lru_cache

from bs4 import BeautifulSoup

from .client import BROWSER_HEADERS, HttpClient, UpstreamError
from .models import Achievement, GithubAchievements


class GithubAchievementsScraper:
    BASE_URL = "https://github.com/"
    USERNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){0,38}$", re.IGNORECASE)

    def __init__(self, client: HttpClient):
        self.client = client
        self.fetch = lru_cache(maxsize=256)(self._fetch)

    @classmethod
    def validate_username(cls, username: str) -> str:
        name = username.strip()
        if not cls.USERNAME_RE.match(name):
            raise ValueError("username must be a valid GitHub username")
        return name

    def _fetch(self, username: str) -> GithubAchievements:
        try:
            html = self.client.get(f"{self.BASE_URL}{username}?tab=achievements", BROWSER_HEADERS)
        except UpstreamError as e:
            if e.status_code == 404:
                raise UpstreamError(404, "GitHub user not found")
            raise
        return self.parse(username, html)

    @classmethod
    def parse(cls, username: str, html: str) -> GithubAchievements:
        soup = BeautifulSoup(html, "html.parser")
        seen: dict[str, Achievement] = {}
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
