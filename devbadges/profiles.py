import datetime as dt
import re
from functools import lru_cache
from typing import Optional

from bs4 import BeautifulSoup

from .client import BROWSER_HEADERS, HttpClient, UpstreamError
from .models import Badge, Profile


class SkillsBoostScraper:
    BASE_URL = "https://www.skills.google/public_profiles/"
    PROFILE_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

    def __init__(self, client: HttpClient):
        self.client = client
        self.fetch = lru_cache(maxsize=256)(self._fetch)

    @classmethod
    def validate_id(cls, profile_id: str) -> str:
        pid = profile_id.strip().lower()
        if not cls.PROFILE_ID_RE.match(pid):
            raise ValueError("profile_id must be a UUID")
        return pid

    def _fetch(self, profile_id: str) -> Profile:
        try:
            html = self.client.get(self.BASE_URL + profile_id, BROWSER_HEADERS)
        except UpstreamError as e:
            if e.status_code == 404:
                raise UpstreamError(404, "Profile not found or not public")
            raise
        return self.parse(profile_id, html)

    @staticmethod
    def parse_earned_date(text: str) -> Optional[str]:
        m = re.search(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", text)
        if not m:
            return None
        try:
            return dt.datetime.strptime(" ".join(m.groups()), "%b %d %Y").date().isoformat()
        except ValueError:
            return None

    @classmethod
    def parse(cls, profile_id: str, html: str) -> Profile:
        soup = BeautifulSoup(html, "html.parser")

        h1 = soup.select_one("main h1")
        avatar = soup.select_one("ql-avatar.profile-avatar")
        member_p = soup.select_one("main p.ql-body-large")
        member_since = None
        if member_p:
            m = re.search(r"\d{4}", member_p.get_text())
            member_since = int(m.group()) if m else None

        badges: list[Badge] = []
        for card in soup.select("div.profile-badge"):
            link = card.select_one("a.badge-image")
            img = link.select_one("img") if link else None
            title_el = card.select_one("span.ql-title-medium")
            earned_el = card.select_one("span.ql-body-medium")

            href = link["href"] if link and link.has_attr("href") else None
            badge_id = None
            if href:
                m = re.search(r"/badges/(\d+)", href)
                badge_id = int(m.group(1)) if m else None

            earned_raw = earned_el.get_text(strip=True) if earned_el else ""
            badges.append(
                Badge(
                    id=badge_id,
                    title=title_el.get_text(strip=True) if title_el else "",
                    earned_at=cls.parse_earned_date(earned_raw),
                    earned_raw=earned_raw,
                    image_url=img["src"] if img and img.has_attr("src") else None,
                    url=href,
                )
            )

        return Profile(
            profile_id=profile_id,
            name=h1.get_text(strip=True) if h1 else None,
            avatar_url=avatar["src"] if avatar and avatar.has_attr("src") else None,
            member_since=member_since,
            badge_count=len(badges),
            badges=badges,
        )
