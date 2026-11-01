from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .client import HttpClient, UpstreamError
from .common import InvalidId
from .constants import (
    API_TITLE,
    API_VERSION,
    DEFAULT_PERLINE,
    DEFAULT_THEME,
    MAX_PERLINE,
    NOTICE_MAX_AGE,
    SVG_MAX_AGE,
    Theme,
)
from .github import AchievementsHidden, GithubAchievementsScraper
from .models import Badge, GithubAchievements, Profile, Weather
from .profiles import SkillsBoostScraper
from .svg import BadgeGridRenderer, GridItem
from .weather import GoogleWeatherScraper

PERLINE = Query(DEFAULT_PERLINE, ge=1, le=MAX_PERLINE, description="Badges per row, like skillicons.dev")
THEME = Query(DEFAULT_THEME, description="Tile background, like skillicons.dev")
SVG_ROUTE = {"methods": ["GET"], "response_class": Response, "responses": {200: {"content": {"image/svg+xml": {}}}}}


class Api:
    def __init__(
        self,
        profiles: SkillsBoostScraper,
        weather: GoogleWeatherScraper,
        github: GithubAchievementsScraper,
        svg: BadgeGridRenderer,
    ):
        self.profiles = profiles
        self.weather = weather
        self.github = github
        self.svg = svg
        self.app = FastAPI(title=API_TITLE, version=API_VERSION)
        self.app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])
        self.app.add_exception_handler(UpstreamError, self.upstream_error)
        self.app.add_exception_handler(InvalidId, self.invalid_id)
        self.app.add_api_route("/", self.root, methods=["GET"])
        self.app.add_api_route("/profile/{profile_id}", self.get_profile, methods=["GET"], response_model=Profile)
        self.app.add_api_route(
            "/profile/{profile_id}/badges", self.get_badges, methods=["GET"], response_model=list[Badge]
        )
        self.app.add_api_route("/profile/{profile_id}/badges.svg", self.get_badges_svg, **SVG_ROUTE)
        self.app.add_api_route(
            "/github/{username}/achievements",
            self.get_achievements,
            methods=["GET"],
            response_model=GithubAchievements,
        )
        self.app.add_api_route("/github/{username}/achievements.svg", self.get_achievements_svg, **SVG_ROUTE)
        self.app.add_api_route("/weather", self.get_weather, methods=["GET"], response_model=Weather)

    @staticmethod
    async def upstream_error(_: Request, exc: UpstreamError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @staticmethod
    async def invalid_id(_: Request, exc: InvalidId) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    def root(self) -> dict:
        return {
            "name": self.app.title,
            "docs": "/docs",
            "endpoints": [
                "/profile/{profile_id}",
                "/profile/{profile_id}/badges",
                "/profile/{profile_id}/badges.svg?perline=6&theme=dark",
                "/github/{username}/achievements",
                "/github/{username}/achievements.svg?perline=6&theme=dark",
                "/weather?query=<text>",
            ],
        }

    @staticmethod
    def svg_response(content: str, max_age: int = SVG_MAX_AGE) -> Response:
        return Response(
            content=content, media_type="image/svg+xml", headers={"Cache-Control": f"public, max-age={max_age}"}
        )

    def get_profile(self, profile_id: str) -> Profile:
        return self.profiles.fetch(self.profiles.validate(profile_id))

    def get_badges(self, profile_id: str) -> list[Badge]:
        return self.get_profile(profile_id).badges

    def get_badges_svg(self, profile_id: str, perline: int = PERLINE, theme: Theme = THEME) -> Response:
        profile = self.get_profile(profile_id)
        items = [GridItem(b.image_url, b.title) for b in profile.badges if b.image_url]
        label = f"Google Cloud Skills Boost badges of {profile.name or profile_id}"
        return self.svg_response(self.svg.render(items, perline, label, theme))

    def get_achievements(self, username: str) -> GithubAchievements:
        return self.github.fetch(self.github.validate(username))

    def get_achievements_svg(self, username: str, perline: int = PERLINE, theme: Theme = THEME) -> Response:
        try:
            data = self.get_achievements(username)
        except AchievementsHidden as e:
            # A README <img> can't show a JSON error, so put the explanation in the picture
            return self.svg_response(self.svg.notice(e.detail, theme), NOTICE_MAX_AGE)
        items = [GridItem(a.image_url, a.name, f"x{a.tier}" if a.tier > 1 else None) for a in data.achievements]
        return self.svg_response(self.svg.render(items, perline, f"GitHub achievements of {data.username}", theme))

    def get_weather(
        self,
        query: str = Query(..., min_length=1, max_length=100, description="Search text, e.g. 'weather in London'"),
    ) -> Weather:
        result = self.weather.fetch(query)
        if result is None:
            raise HTTPException(status_code=404, detail="No weather card found for that query")
        return result


def create_app() -> FastAPI:
    client = HttpClient()
    return Api(
        SkillsBoostScraper(client),
        GoogleWeatherScraper(client),
        GithubAchievementsScraper(client),
        BadgeGridRenderer(client),
    ).app
