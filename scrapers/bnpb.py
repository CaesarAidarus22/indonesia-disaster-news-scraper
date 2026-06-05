from __future__ import annotations

import logging
from typing import Iterable

from bs4 import BeautifulSoup

from scrapers.base import BaseNewsScraper, SourceConfig
from utils.text import clean_text


class BNPBScraper(BaseNewsScraper):
    def __init__(self, client=None) -> None:
        super().__init__(
            SourceConfig(
                name="BNPB.go.id",
                base_url="https://www.bnpb.go.id/",
                search_urls=[
                    "https://www.bnpb.go.id/berita?search={query}",
                    "https://www.bnpb.go.id/search?q={query}",
                ],
                link_allow_patterns=[r"/berita/"],
                title_selectors=["h1", ".detail-title", ".entry-title"],
                date_selectors=["time", ".date", ".detail-date", ".post-date"],
                author_selectors=[".author", ".post-author"],
                content_selectors=["article", ".detail-content", ".entry-content", ".post-content"],
            ),
            client=client,
        )
        self._search_unavailable_logged = False

    def get_article_links(
        self,
        keywords: Iterable[str],
        max_pages: int = 1,
        archive_days: int = 0,
    ) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()
        self.unique_urls_found = 0
        self.duplicate_urls_skipped = 0
        self.archive_urls_found = 0
        self.archive_urls_skipped = 0
        self.archive_urls_after_filter = 0

        for keyword in keywords:
            for url_template in self.config.search_urls[:max_pages]:
                search_url = url_template.format(query=keyword.replace(" ", "+"))
                if not self.client.can_fetch(search_url):
                    logging.info("Skipping disallowed URL by robots.txt: %s", search_url)
                    continue

                html, status_code = self.client.get_with_status(search_url, log_errors=False)
                if status_code and status_code >= 500:
                    self._log_search_unavailable_once()
                    self.unique_urls_found = len(seen)
                    return links
                if not html:
                    continue

                soup = BeautifulSoup(html, "lxml")
                self._collect_links_from_soup(
                    soup,
                    links,
                    seen,
                    require_article_hint=True,
                    context_text=search_url,
                )

        self.unique_urls_found = len(seen)
        return links

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)

    def _log_search_unavailable_once(self) -> None:
        if not self._search_unavailable_logged:
            logging.info("BNPB search unavailable, skipping BNPB")
            self._search_unavailable_logged = True
