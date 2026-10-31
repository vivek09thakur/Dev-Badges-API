# DevBadges API
Read-only API for showing off your dev profile: Google Cloud Skills Boost badges (JSON), GitHub achievements (JSON or an embeddable SVG), plus a Google weather-card scraper.

## Endpoints
| Method | Path | Returns |
| --- | --- | --- |
| GET | `/profile/{profile_id}` | Skills Boost name, avatar, member_since, badges[] |
| GET | `/profile/{profile_id}/badges` | Skills Boost badges[] only |
| GET | `/github/{username}/achievements` | GitHub achievements[] with slug, name, tier, image_url |
| GET | `/github/{username}/achievements.svg?perline=6` | One SVG with all achievement badges in a grid |
| GET | `/weather?query=weather+in+London` | temp, time, sky |

Interactive docs at `/docs`.

## Embed GitHub achievements in a README
Works like skillicons.dev — one `<img>`, `perline` controls the grid width:

```html
<img src="https://<your-deployment>/github/<username>/achievements.svg?perline=6" width="48%" align="top" />
```

Badge images are inlined into the SVG, so it renders anywhere `<img>` does (GitHub READMEs included). Tier multipliers (x2, x3…) are drawn as pills, matching GitHub's profile sidebar.

## Run locally
```bash
pip install -r requirements.txt uvicorn
uvicorn main:app --reload
```

CLI (no server): `python main.py <profile_id>`

## Layout
```
main.py                 # entry point: app = create_app(); CLI
devbadges/
  models.py             # Badge, Profile, Weather, Achievement (pydantic)
  client.py             # HttpClient + UpstreamError
  profiles.py           # SkillsBoostScraper
  github.py             # GithubAchievementsScraper + AchievementsSvgRenderer
  weather.py            # GoogleWeatherScraper
  api.py                # Api (routes) + create_app()
```
