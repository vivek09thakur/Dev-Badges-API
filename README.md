# DevBadges API
Read-only API for showing off your dev profile: Google Cloud Skills Boost badges (JSON), GitHub achievements (JSON or an embeddable SVG), plus a Google weather-card scraper.

## Endpoints
| Method | Path | Returns |
| --- | --- | --- |
| GET | `/profile/{profile_id}` | Skills Boost name, avatar, member_since, badges[] |
| GET | `/profile/{profile_id}/badges` | Skills Boost badges[] only |
| GET | `/profile/{profile_id}/badges.svg?perline=6` | One SVG with all Skills Boost badges in a grid |
| GET | `/github/{username}/achievements` | GitHub achievements[] with slug, name, tier, image_url |
| GET | `/github/{username}/achievements.svg?perline=6` | One SVG with all achievement badges in a grid |
| GET | `/weather?query=weather+in+London` | temp, time, sky |

Interactive docs at `/docs`.

## Embed badges in a README
Works like skillicons.dev — one `<img>`, `perline` controls the grid width:

```html
<img src="https://dev-badges.vercel.app/github/<username>/achievements.svg?perline=6" width="48%" align="top" />
<img src="https://dev-badges.vercel.app/profile/<profile_id>/badges.svg?perline=6" width="48%" align="top" />
```

Badge images are downscaled to 128 px and inlined into the SVG, so it renders anywhere `<img>` does (GitHub READMEs included). GitHub tier multipliers (x2, x3…) are drawn as pills, matching the profile sidebar.

## Run locally
```bash
pip install -r requirements.txt uvicorn
uvicorn main:app --reload
```