from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36 NLPDisasterResearchBot/1.0"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.7,en;q=0.6",
}


@dataclass
class HttpClient:
    delay_seconds: float = 1.5
    timeout_seconds: int = 15

    def __post_init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.user_agent = DEFAULT_HEADERS["User-Agent"]
        self._robots_cache: dict[str, RobotFileParser | None] = {}

    def get(self, url: str) -> str | None:
        time.sleep(self.delay_seconds)
        try:
            response = self.session.get(url, timeout=self.timeout_seconds)
            if response.status_code == 404:
                logging.warning("404 not found: %s", url)
                return None
            response.raise_for_status()
            if not response.encoding:
                response.encoding = response.apparent_encoding
            return response.text
        except requests.exceptions.Timeout:
            logging.warning("Timeout when fetching %s", url)
        except requests.exceptions.ConnectionError:
            logging.warning("Connection failed when fetching %s", url)
        except requests.exceptions.HTTPError as exc:
            logging.warning("HTTP error for %s: %s", url, exc)
        except requests.exceptions.RequestException as exc:
            logging.warning("Request failed for %s: %s", url, exc)
        return None

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False

        base_url = f"{parsed.scheme}://{parsed.netloc}/"
        if base_url not in self._robots_cache:
            self._robots_cache[base_url] = self._load_robots(base_url)

        robot_parser = self._robots_cache[base_url]
        if robot_parser is None:
            return True
        return robot_parser.can_fetch(self.user_agent, url)

    def _load_robots(self, base_url: str) -> RobotFileParser | None:
        robots_url = urljoin(base_url, "robots.txt")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            response = self.session.get(robots_url, timeout=self.timeout_seconds)
            if response.status_code >= 400:
                logging.warning("robots.txt unavailable for %s: %s", base_url, response.status_code)
                return None
            parser.parse(response.text.splitlines())
            return parser
        except requests.exceptions.RequestException as exc:
            logging.warning("Failed to read robots.txt for %s: %s", base_url, exc)
            return None
