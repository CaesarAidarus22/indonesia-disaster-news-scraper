from __future__ import annotations

from typing import Iterable

from scrapers.base import SourceConfig
from scrapers.portal import DisasterPortalScraper


class OkezoneScraper(DisasterPortalScraper):
    def __init__(self, client=None) -> None:
        super().__init__(
            SourceConfig(
                name="Okezone.com",
                base_url="https://www.okezone.com/",
                search_urls=[
                    "https://search.okezone.com/search?q={query}",
                    "https://www.okezone.com/search?q={query}",
                ],
                archive_url_templates=[
                    "https://index.okezone.com/bydate/{date}/{page}",
                ],
                category_urls=[
                    "https://nasional.okezone.com/",
                    "https://news.okezone.com/",
                    "https://megapolitan.okezone.com/",
                    "https://www.okezone.com/tag/banjir",
                    "https://www.okezone.com/tag/gempa",
                    "https://www.okezone.com/tag/bencana",
                ],
                link_allow_patterns=[
                    r"(nasional|news|megapolitan)\.okezone\.com/read/\d{4}/\d{2}/\d{2}/",
                ],
                title_selectors=["h1", ".title", ".read-title"],
                date_selectors=["time", ".namerep", ".date"],
                author_selectors=[".author", ".reporter", "[rel='author']"],
                content_selectors=[".read", ".article-content", ".content", "article"],
                remove_selectors=[".baca-juga", ".related", ".ads"],
            ),
            client=client,
        )

    def get_article_links(self, keywords: Iterable[str], max_pages: int = 1, archive_days: int = 0) -> list[str]:
        return super().get_article_links(keywords, max_pages=max_pages, archive_days=archive_days)

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)
