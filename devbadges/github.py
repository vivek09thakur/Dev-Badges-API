import re

from .client import UpstreamError
from .common import Scraper, make_soup
from .constants import GITHUB_URL, GITHUB_USERNAME_RE
from .models import Achievement, GithubAchievements


class AchievementsHidden(UpstreamError):
    """The profile exists but lists no achievements: GitHub's 'Show Achievements on my profile' is off."""

    def __init__(self, username: str):
        super().__init__(
            404,
            f"github.com/{username} shows no achievements. Turn on 'Show Achievements on my profile' "
            "in GitHub Settings > Public profile.",
        )


class GithubAchievementsScraper(Scraper[GithubAchievements]):
    BASE_URL = GITHUB_URL
    ID_RE = GITHUB_USERNAME_RE
    ID_ERROR = "username must be a valid GitHub username"
    NOT_FOUND = "GitHub user not found"

    def _fetch(self, username: str) -> GithubAchievements:
        result = super()._fetch(username)
        if not result.achievements:
            raise AchievementsHidden(username)
        return result

    @classmethod
    def parse(cls, username: str, html: str) -> GithubAchievements:
        seen: dict[str, Achievement] = {}
        for img in make_soup(html).select("img.achievement-badge-sidebar"):
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
