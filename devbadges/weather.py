import urllib.parse
from typing import Optional

from .client import HttpClient
from .common import make_soup
from .constants import GOOGLE_SEARCH_URL
from .models import Weather


class GoogleWeatherScraper:
    def __init__(self, client: HttpClient):
        self.client = client

    def fetch(self, query: str) -> Optional[Weather]:
        return self.parse(self.client.get(GOOGLE_SEARCH_URL + urllib.parse.quote_plus(query)))

    @staticmethod
    def parse(html: str) -> Optional[Weather]:
        soup = make_soup(html)
        temp = soup.select_one("div.BNeawe.iBp4i.AP7Wnd")
        desc = soup.select_one("div.BNeawe.tAd8D.AP7Wnd")
        if not temp or not desc:
            return None
        lines = desc.get_text().split("\n")
        if len(lines) < 2:
            return None
        return Weather(temp=temp.get_text(strip=True), time=lines[0][:-3], sky=lines[1])
