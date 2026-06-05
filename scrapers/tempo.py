from __future__ import annotations

from typing import Iterable

from scrapers.base import SourceConfig
from scrapers.sitemap import SitemapFirstNewsScraper


class TempoScraper(SitemapFirstNewsScraper):
    sitemap_urls = [
        "https://www.tempo.co/sitemap.xml",
        "https://www.tempo.co/sitemap-news.xml",
    ]
    category_urls = [
        "https://www.tempo.co/nasional",
        "https://www.tempo.co/hukum",
        "https://www.tempo.co/lingkungan",
    ]

    def __init__(self, client=None) -> None:
        super().__init__(
            SourceConfig(
                name="Tempo.co",
                base_url="https://www.tempo.co/",
                search_urls=[],
                link_allow_patterns=[r"tempo\.co/.+"],
                title_selectors=["h1", ".detail-title", ".title"],
                date_selectors=["time", ".date", ".detail-date"],
                author_selectors=[".author", ".detail-author", "[rel='author']"],
                content_selectors=["article", ".detail-in", ".detail-content", ".article-content"],
                remove_selectors=[".related", ".read-also", ".iklan", ".ads"],
            ),
            client=client,
        )

    def get_article_links(self, keywords: Iterable[str], max_pages: int = 1) -> list[str]:
        return super().get_article_links(keywords=keywords, max_pages=max_pages)

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)
