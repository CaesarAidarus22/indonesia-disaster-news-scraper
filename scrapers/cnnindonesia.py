from __future__ import annotations

from typing import Iterable

from scrapers.base import SourceConfig
from scrapers.portal import DisasterPortalScraper


class CNNIndonesiaScraper(DisasterPortalScraper):
    sitemap_urls = [
        "https://www.cnnindonesia.com/sitemap.xml",
        "https://www.cnnindonesia.com/nasional/sitemap_news.xml",
        "https://www.cnnindonesia.com/nasional/sitemap_web.xml",
    ]
    sitemap_allow_keywords = [
        "/nasional/sitemap_news",
        "/nasional/sitemap_web",
    ]

    def __init__(self, client=None) -> None:
        super().__init__(
            SourceConfig(
                name="CNNIndonesia.com",
                base_url="https://www.cnnindonesia.com/",
                search_urls=[],
                category_urls=[
                    "https://www.cnnindonesia.com/nasional",
                    "https://www.cnnindonesia.com/tag/bencana",
                    "https://www.cnnindonesia.com/tag/banjir",
                    "https://www.cnnindonesia.com/tag/gempa",
                ],
                link_allow_patterns=[r"cnnindonesia\.com/.+/\d{8,}"],
                title_selectors=["h1", ".title"],
                date_selectors=["time", ".text-cnn_grey", ".date"],
                author_selectors=[".author", ".detail-author"],
                content_selectors=[".detail-text", "article"],
                remove_selectors=[".paradetail", ".video", ".read__right", ".box"],
            ),
            client=client,
        )

    def get_article_links(self, keywords: Iterable[str], max_pages: int = 1, archive_days: int = 0) -> list[str]:
        return super().get_article_links(keywords, max_pages=max_pages, archive_days=archive_days)

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)
