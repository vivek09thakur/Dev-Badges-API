#!/usr/bin/env python3
import json
import sys

from devbadges import create_app
from devbadges.client import HttpClient
from devbadges.profiles import SkillsBoostScraper

app = create_app()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python main.py <profile_id>")
    scraper = SkillsBoostScraper(HttpClient())
    print(json.dumps(scraper.fetch(scraper.validate_id(sys.argv[1])).model_dump(), indent=2))
