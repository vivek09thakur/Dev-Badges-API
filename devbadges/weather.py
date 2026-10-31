import urllib.parse
from typing import Optional

from bs4 import BeautifulSoup

from .client import HttpClient
from .models import Weather


class GoogleWeatherScraper:
    # Google only serves the plain-HTML weather card we parse to non-browser User-Agents,
    # so this request is deliberately sent without browser headers.
    URL = "https://www.google.com/search?hl=en&q="

    def __init__(self, client: HttpClient):
        self.client = client

    def fetch(self, query: str) -> Optional[Weather]:
        return self.parse(self.client.get(self.URL + urllib.parse.quote_plus(query)))

    @staticmethod
    def parse(html: str) -> Optional[Weather]:
        soup = BeautifulSoup(html, "html.parser")
        temp = soup.select_one("div.BNeawe.iBp4i.AP7Wnd")
        desc = soup.select_one("div.BNeawe.tAd8D.AP7Wnd")
        if not temp or not desc:
            return None
        lines = desc.get_text().split("\n")
        if len(lines) < 2:
            return None
        return Weather(temp=temp.get_text(strip=True), time=lines[0][:-3], sky=lines[1])
