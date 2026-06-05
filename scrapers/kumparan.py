from __future__ import annotations

from typing import Iterable

from scrapers.base import SourceConfig
from scrapers.sitemap import SitemapFirstNewsScraper


class KumparanScraper(SitemapFirstNewsScraper):
    sitemap_urls = [
        "https://kumparan.com/sitemap.xml",
        "https://kumparan.com/sitemap-news.xml",
    ]
    category_urls = [
        "https://kumparan.com/topic/bencana",
        "https://kumparan.com/topic/banjir",
        "https://kumparan.com/topic/gempa",
        "https://kumparan.com/topic/peristiwa",
        "https://kumparan.com/news",
    ]

    def __init__(self, client=None) -> None:
        super().__init__(
            SourceConfig(
                name="Kumparan.com",
                base_url="https://kumparan.com/",
                search_urls=[],
                link_allow_patterns=[r"kumparan\.com/.+/"],
                title_selectors=["h1", "[data-qa-id='story-title']", ".title"],
                date_selectors=["time", "[datetime]", ".date"],
                author_selectors=["[data-qa-id='author-name']", ".author", "[rel='author']"],
                content_selectors=["article", "[data-qa-id='story-content']", ".story-content", ".content"],
                remove_selectors=[".related", ".ads", "[data-qa-id='read-more']"],
            ),
            client=client,
        )

    def get_article_links(
        self,
        keywords: Iterable[str],
        max_pages: int = 1,
        archive_days: int = 0,
    ) -> list[str]:
        return super().get_article_links(
            keywords=keywords,
            max_pages=max_pages,
            archive_days=archive_days,
        )

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)
