from __future__ import annotations

from typing import Iterable

from scrapers.base import SourceConfig
from scrapers.portal import DisasterPortalScraper


class SuaraScraper(DisasterPortalScraper):
    def __init__(self, client=None) -> None:
        super().__init__(
            SourceConfig(
                name="Suara.com",
                base_url="https://www.suara.com/",
                search_urls=[
                    "https://www.suara.com/search?q={query}",
                ],
                archive_url_templates=[
                    "https://www.suara.com/indeks/{date}?page={page}",
                ],
                category_urls=[
                    "https://www.suara.com/news",
                    "https://www.suara.com/tag/bencana",
                    "https://www.suara.com/tag/banjir",
                    "https://www.suara.com/tag/gempa",
                    "https://www.suara.com/tag/kebakaran",
                ],
                link_allow_patterns=[
                    r"suara\.com/news/\d{4}/\d{2}/\d{2}/",
                ],
                title_selectors=["h1", ".title", ".article-title"],
                date_selectors=["time", ".date", ".info-date"],
                author_selectors=[".author", ".writer", "[rel='author']"],
                content_selectors=["article", ".article-content", ".content-article", ".detail-content"],
                remove_selectors=[".baca-juga", ".related", ".ads", ".share"],
            ),
            client=client,
        )

    def get_article_links(self, keywords: Iterable[str], max_pages: int = 1, archive_days: int = 0) -> list[str]:
        return super().get_article_links(keywords, max_pages=max_pages, archive_days=archive_days)

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)
