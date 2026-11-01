import datetime as dt
import re
from typing import Optional

from .common import Scraper, make_soup
from .constants import SKILLS_BOOST_ID_RE, SKILLS_BOOST_URL
from .models import Badge, Profile


class SkillsBoostScraper(Scraper[Profile]):
    BASE_URL = SKILLS_BOOST_URL
    ID_RE = SKILLS_BOOST_ID_RE
    ID_ERROR = "profile_id must be a UUID"
    NOT_FOUND = "Profile not found or not public"

    @classmethod
    def validate(cls, profile_id: str) -> str:
        return super().validate(profile_id.lower())

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
        soup = make_soup(html)

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
