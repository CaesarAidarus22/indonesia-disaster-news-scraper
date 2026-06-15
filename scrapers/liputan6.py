from __future__ import annotations

import logging
from typing import Iterable

from scrapers.base import SourceConfig
from scrapers.sitemap import SitemapFirstNewsScraper


LIPUTAN6_SEARCH_KEYWORDS = [
    "banjir",
    "gempa bumi",
    "tsunami",
    "tanah longsor",
    "kebakaran",
    "erupsi",
]


class Liputan6Scraper(SitemapFirstNewsScraper):
    sitemap_urls = [
        "https://www.liputan6.com/sitemap.xml",
        "https://www.liputan6.com/sitemap-news.xml",
    ]
    category_urls = [
        "https://www.liputan6.com/news",
        "https://www.liputan6.com/regional",
        "https://www.liputan6.com/tag/bencana",
        "https://www.liputan6.com/tag/banjir",
        "https://www.liputan6.com/tag/gempa-bumi",
        "https://www.liputan6.com/tag/tsunami",
        "https://www.liputan6.com/tag/tanah-longsor",
        "https://www.liputan6.com/tag/kebakaran",
        "https://www.liputan6.com/tag/erupsi",
        "https://www.liputan6.com/indeks",
    ]

    def __init__(self, client=None) -> None:
        super().__init__(
            SourceConfig(
                name="Liputan6.com",
                base_url="https://www.liputan6.com/",
                search_urls=[
                    "https://www.liputan6.com/search?q={query}",
                ],
                archive_url_templates=[
                    "https://www.liputan6.com/indeks/{year}/{month}/{day}?page={page}",
                    "https://www.liputan6.com/indeks?date={date}&page={page}",
                ],
                link_allow_patterns=[r"liputan6\.com/.+/read/\d+"],
                title_selectors=[
                    "h1",
                    ".read-page--header--title",
                    ".article-header h1",
                ],
                date_selectors=[
                    "time",
                    ".read-page--header--date",
                    ".article-header .date",
                    ".date",
                ],
                author_selectors=[
                    ".read-page--header--author",
                    ".article-header .author",
                    ".author",
                    "[rel='author']",
                ],
                content_selectors=[
                    ".article-content-body__item-content",
                    ".read-page--article-content-body",
                    ".article-content-body",
                    "article",
                ],
                remove_selectors=[
                    ".read-page--related",
                    ".baca-juga",
                    ".ads",
                    ".advertisement",
                    ".share",
                ],
            ),
            client=client,
        )

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

        self._collect_from_sitemaps(links, seen, max_pages=max_pages, archive_days=archive_days)
        self._collect_from_categories(selected_keywords, links, seen, max_pages=max_pages)
        self._collect_from_search_pages(links, seen, keywords=selected_keywords, max_pages=max_pages)

        self.unique_urls_found = len(seen)
        logging.info("Found %d candidate links from Liputan6.com", len(links))
        return links

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)

    def _select_keywords(self, keywords: Iterable[str]) -> list[str]:
        allowed = {keyword.casefold(): keyword for keyword in LIPUTAN6_SEARCH_KEYWORDS}
        requested = [allowed[keyword.casefold()] for keyword in keywords if keyword.casefold() in allowed]
        return requested or LIPUTAN6_SEARCH_KEYWORDS
