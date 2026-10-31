from typing import Optional

from pydantic import BaseModel


class Badge(BaseModel):
    id: Optional[int]
    title: str
    earned_at: Optional[str]  # ISO date (YYYY-MM-DD)
    earned_raw: str
    image_url: Optional[str]
    url: Optional[str]


class Profile(BaseModel):
    profile_id: str
    name: Optional[str]
    avatar_url: Optional[str]
    member_since: Optional[int]
    badge_count: int
    badges: list[Badge]


class Weather(BaseModel):
    temp: str
    time: str
    sky: str


class Achievement(BaseModel):
    slug: str
    name: str
    tier: int  # 1 = base badge, 2+ = the "xN" multiplier GitHub shows
    image_url: str
    url: str


class GithubAchievements(BaseModel):
    username: str
    count: int
    achievements: list[Achievement]
