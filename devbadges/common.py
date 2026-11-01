import re
from functools import lru_cache
from typing import Generic, TypeVar

from bs4 import BeautifulSoup

from .client import HttpClient, UpstreamError
from .constants import BROWSER_HEADERS, CACHE_SIZE, HTML_PARSER

T = TypeVar("T")


class InvalidId(ValueError):
    """Caller-supplied id/username failed validation; raised before any network call. The API maps it to 400."""


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, HTML_PARSER)


class Scraper(Generic[T]):
    """Validate an id, fetch one upstream page, parse it. Results are memoised per id; errors are not."""

    BASE_URL: str
    ID_RE: re.Pattern[str]
    ID_ERROR: str
    NOT_FOUND: str

    def __init__(self, client: HttpClient):
        self.client = client
        self.fetch = lru_cache(maxsize=CACHE_SIZE)(self._fetch)

    @classmethod
    def validate(cls, value: str) -> str:
        value = value.strip()
        if not cls.ID_RE.match(value):
            raise InvalidId(cls.ID_ERROR)
        return value

    def fetch_html(self, url: str) -> str:
        try:
            return self.client.get(url, BROWSER_HEADERS)
        except UpstreamError as e:
            if e.status_code == 404:
                raise UpstreamError(404, self.NOT_FOUND)
            raise

    def _fetch(self, key: str) -> T:
        return self.parse(key, self.fetch_html(self.BASE_URL + key))

    @classmethod
    def parse(cls, key: str, html: str) -> T:
        raise NotImplementedError
