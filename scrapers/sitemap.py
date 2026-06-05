from __future__ import annotations

import logging
import re
from typing import Iterable

from bs4 import BeautifulSoup

from scrapers.base import BaseNewsScraper, SourceConfig
from utils.text import clean_text


class SitemapFirstNewsScraper(BaseNewsScraper):
    sitemap_urls: list[str] = []
    category_urls: list[str] = []

    def __init__(self, config: SourceConfig, client=None) -> None:
        super().__init__(config=config, client=client)

    def get_article_links(self, keywords: Iterable[str], max_pages: int = 1) -> list[str]:
        links = self._collect_from_sitemaps(keywords, max_pages=max_pages)
        if links:
            return links

        logging.info("No sitemap links found for %s, falling back to category pages", self.config.name)
        return self._collect_from_categories(keywords, max_pages=max_pages)

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)

    def _collect_from_sitemaps(self, keywords: Iterable[str], max_pages: int) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()
        sitemap_queue = self.sitemap_urls[:max_pages]
        processed = 0
        max_sitemaps = max(1, max_pages) * 8

        while sitemap_queue and processed < max_sitemaps:
            sitemap_url = sitemap_queue.pop(0)
            processed += 1
            if not self.client.can_fetch(sitemap_url):
                logging.info("Skipping disallowed sitemap by robots.txt: %s", sitemap_url)
                continue

            html = self.client.get(sitemap_url)
            if not html:
                continue

            soup = BeautifulSoup(html, "xml")
            child_sitemaps = [loc.get_text(strip=True) for loc in soup.select("sitemap loc")]
            if child_sitemaps:
                sitemap_queue.extend(child_sitemaps[:max_pages])
                continue

            for loc in soup.select("url loc"):
                url = self._normalize_url(loc.get_text(strip=True))
                if not url or url in seen:
                    continue
                if not self.client.can_fetch(url):
                    logging.info("Skipping disallowed article link by robots.txt: %s", url)
                    continue
                if self._matches_keyword(url, keywords) and self._looks_like_article_url(url, ""):
                    seen.add(url)
                    links.append(url)

        return links

    def _collect_from_categories(self, keywords: Iterable[str], max_pages: int) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()

        for category_url in self.category_urls[:max_pages]:
            if not self.client.can_fetch(category_url):
                logging.info("Skipping disallowed category by robots.txt: %s", category_url)
                continue

            html = self.client.get(category_url)
            if not html:
                continue

            soup = BeautifulSoup(html, "lxml")
            for anchor in soup.find_all("a", href=True):
                url = self._normalize_url(anchor.get("href"))
                if not url or url in seen:
                    continue
                if not self.client.can_fetch(url):
                    logging.info("Skipping disallowed article link by robots.txt: %s", url)
                    continue
                anchor_text = clean_text(anchor.get_text(" "))
                if self._matches_keyword(f"{url} {anchor_text}", keywords) and self._looks_like_article_url(url, anchor_text):
                    seen.add(url)
                    links.append(url)

        return links

    def _matches_keyword(self, text: str, keywords: Iterable[str]) -> bool:
        normalized = re.sub(r"[-_+%20]+", " ", text.casefold())
        for keyword in keywords:
            normalized_keyword = re.sub(r"\s+", " ", keyword.casefold()).strip()
            if re.search(rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)", normalized):
                return True
        return False
