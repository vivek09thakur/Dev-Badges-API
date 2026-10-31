from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .client import HttpClient, UpstreamError
from .github import AchievementsSvgRenderer, GithubAchievementsScraper
from .models import Badge, GithubAchievements, Profile, Weather
from .profiles import SkillsBoostScraper
from .weather import GoogleWeatherScraper


class Api:
    def __init__(
        self,
        profiles: SkillsBoostScraper,
        weather: GoogleWeatherScraper,
        github: GithubAchievementsScraper,
        svg: AchievementsSvgRenderer,
    ):
        self.profiles = profiles
        self.weather = weather
        self.github = github
        self.svg = svg
        self.app = FastAPI(title="DevBadges API", version="2.0.0")
        self.app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])
        self.app.add_exception_handler(UpstreamError, self.upstream_error)
        self.app.add_api_route("/", self.root, methods=["GET"])
        self.app.add_api_route("/profile/{profile_id}", self.get_profile, methods=["GET"], response_model=Profile)
        self.app.add_api_route(
            "/profile/{profile_id}/badges", self.get_badges, methods=["GET"], response_model=list[Badge]
        )
        self.app.add_api_route("/weather", self.get_weather, methods=["GET"], response_model=Weather)
        self.app.add_api_route(
            "/github/{username}/achievements.svg",
            self.get_achievements_svg,
            methods=["GET"],
            response_class=Response,
            responses={200: {"content": {"image/svg+xml": {}}}},
        )
        self.app.add_api_route(
            "/github/{username}/achievements",
            self.get_achievements,
            methods=["GET"],
            response_model=GithubAchievements,
        )

    @staticmethod
    async def upstream_error(_: Request, exc: UpstreamError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    def root(self) -> dict:
        return {
            "name": self.app.title,
            "docs": "/docs",
            "endpoints": [
                "/profile/{profile_id}",
                "/profile/{profile_id}/badges",
                "/github/{username}/achievements",
                "/github/{username}/achievements.svg?perline=6",
                "/weather?query=<text>",
            ],
        }

    def get_profile(self, profile_id: str) -> Profile:
        try:
            pid = self.profiles.validate_id(profile_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return self.profiles.fetch(pid)

    def get_badges(self, profile_id: str) -> list[Badge]:
        return self.get_profile(profile_id).badges

    def get_weather(
        self,
        query: str = Query(..., min_length=1, max_length=100, description="Search text, e.g. 'weather in London'"),
    ) -> Weather:
        result = self.weather.fetch(query)
        if result is None:
            raise HTTPException(status_code=404, detail="No weather card found for that query")
        return result

    def get_achievements(self, username: str) -> GithubAchievements:
        try:
            name = self.github.validate_username(username)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return self.github.fetch(name)

    def get_achievements_svg(
        self,
        username: str,
        perline: int = Query(6, ge=1, le=20, description="Badges per row, like skillicons.dev"),
    ) -> Response:
        svg = self.svg.render(self.get_achievements(username), perline)
        return Response(content=svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


def create_app() -> FastAPI:
    client = HttpClient()
    github = GithubAchievementsScraper(client)
    return Api(
        SkillsBoostScraper(client),
        GoogleWeatherScraper(client),
        github,
        AchievementsSvgRenderer(github),
    ).app
