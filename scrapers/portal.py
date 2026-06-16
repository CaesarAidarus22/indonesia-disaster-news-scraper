from __future__ import annotations

import logging
from typing import Iterable

from scrapers.base import SourceConfig
from scrapers.sitemap import SitemapFirstNewsScraper


PORTAL_DISASTER_KEYWORDS = [
    "banjir",
    "gempa bumi",
    "tsunami",
    "tanah longsor",
    "kebakaran",
    "kebakaran hutan",
    "karhutla",
    "erupsi",
    "gunung meletus",
    "puting beliung",
    "kekeringan",
    "abrasi",
    "gelombang tinggi",
    "pengungsi",
    "evakuasi",
    "korban jiwa",
    "bantuan logistik",
    "BNPB",
    "BPBD",
]


class DisasterPortalScraper(SitemapFirstNewsScraper):
    def __init__(self, config: SourceConfig, client=None) -> None:
        super().__init__(config=config, client=client)

    def get_article_links(
        self,
        keywords: Iterable[str],
        max_pages: int = 1,
        archive_days: int = 0,
    ) -> list[str]:
        selected_keywords = self._select_keywords(keywords)
        links: list[str] = []
        seen: set[str] = set()
        self.unique_urls_found = 0
        self.duplicate_urls_skipped = 0
        self.archive_urls_found = 0
        self.archive_urls_skipped = 0
        self.archive_urls_after_filter = 0
        self.sitemap_urls_found = 0
        self.category_urls_found = 0
        self.article_urls_before_filter = 0
        self.article_urls_after_filter = 0

        self._collect_from_sitemaps(links, seen, max_pages=max_pages, archive_days=archive_days)
        self._collect_from_categories(selected_keywords, links, seen, max_pages=max_pages)
        self._collect_from_search_pages(links, seen, keywords=selected_keywords, max_pages=max_pages)

        self.unique_urls_found = len(seen)
        logging.info("Found %d candidate links from %s", len(links), self.config.name)
        return links

    def _collect_from_search_pages(
        self,
        links: list[str],
        seen: set[str],
        keywords: Iterable[str],
        max_pages: int,
    ) -> None:
        for keyword in keywords:
            for url_template in self.config.search_urls[:max_pages]:
                query_value = self._keyword_slug(keyword) if "/tag/" in url_template or "/topic/" in url_template else keyword.replace(" ", "+")
                search_url = url_template.format(query=query_value)
                if not self.client.can_fetch(search_url):
                    logging.info("Skipping disallowed URL by robots.txt: %s", search_url)
                    continue
                html = self.client.get(search_url)
                if not html:
                    continue

                from bs4 import BeautifulSoup

                soup = BeautifulSoup(html, "lxml")
                self._collect_links_from_soup(
                    soup,
                    links,
                    seen,
                    require_article_hint=not self._is_disaster_context(search_url),
                    context_text=search_url,
                )

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)

    def _select_keywords(self, keywords: Iterable[str]) -> list[str]:
        allowed = {keyword.casefold(): keyword for keyword in PORTAL_DISASTER_KEYWORDS}
        requested = [allowed[keyword.casefold()] for keyword in keywords if keyword.casefold() in allowed]
        return requested or PORTAL_DISASTER_KEYWORDS
