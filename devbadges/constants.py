import re
from typing import Literal

# HTTP
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,image/*;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
HTTP_TIMEOUT = 20
CACHE_SIZE = 256
HTML_PARSER = "html.parser"
ICON_WORKERS = 8

# Upstreams
GITHUB_URL = "https://github.com/"
GITHUB_USERNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){0,38}$", re.IGNORECASE)
SKILLS_BOOST_URL = "https://www.skills.google/public_profiles/"
SKILLS_BOOST_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
GOOGLE_SEARCH_URL = "https://www.google.com/search?hl=en&q="

# API
API_TITLE = "DevBadges API"
API_VERSION = "2.2.0"
DEFAULT_PERLINE = 6
MAX_PERLINE = 20
Theme = Literal["dark", "light"]
DEFAULT_THEME: Theme = "dark"
SVG_MAX_AGE = 3600
NOTICE_MAX_AGE = 300
TILE = 64
PAD = 8
GAP = 10
RADIUS = 15
MAX_ASPECT = 2
TILE_FILL = {"dark": "#242938", "light": "#F4F2ED"}
TEXT_FILL = {"dark": "#E6EDF3", "light": "#1F2328"}
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
NOTICE_FONT_SIZE = 13
NOTICE_LINE_HEIGHT = 20
NOTICE_CHAR_WIDTH = 7
NOTICE_WRAP = 44
