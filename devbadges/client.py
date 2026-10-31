import ssl
import urllib.error
import urllib.request
from typing import Optional

# Skills Boost and the badge CDNs return 403 for non-browser User-Agents.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,image/*;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class UpstreamError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class HttpClient:
    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        # Uses the OS trust store (works behind corporate TLS proxies, unlike certifi).
        self.ctx = ssl.create_default_context()

    def get_bytes(self, url: str, headers: Optional[dict[str, str]] = None) -> bytes:
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ctx) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise UpstreamError(404 if e.code == 404 else 502, f"Upstream returned {e.code}")
        except urllib.error.URLError as e:
            raise UpstreamError(502, f"Upstream unreachable: {e.reason}")

    def get(self, url: str, headers: Optional[dict[str, str]] = None) -> str:
        return self.get_bytes(url, headers).decode("utf-8", errors="replace")
