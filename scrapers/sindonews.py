from __future__ import annotations

from typing import Iterable

from scrapers.base import SourceConfig
from scrapers.portal import DisasterPortalScraper


class SindonewsScraper(DisasterPortalScraper):
    sitemap_urls = [
        "https://www.sindonews.com/sitemap.xml",
        "https://www.sindonews.com/sitemap-news.xml",
        "https://nasional.sindonews.com/sitemap.xml",
        "https://nasional.sindonews.com/sitemap-news.xml",
        "https://nasional.sindonews.com/sitemap-web.xml",
        "https://daerah.sindonews.com/sitemap.xml",
        "https://daerah.sindonews.com/sitemap-news.xml",
        "https://daerah.sindonews.com/sitemap-web.xml",
    ]
    sitemap_allow_keywords = [
        "nasional.sindonews.com/sitemap",
        "daerah.sindonews.com/sitemap",
    ]

    def __init__(self, client=None) -> None:
        super().__init__(
            SourceConfig(
                name="Sindonews.com",
                base_url="https://www.sindonews.com/",
                search_urls=[],
                archive_url_templates=[
                    "https://index.sindonews.com/index/0/{date}/{page}",
                ],
                category_urls=[
                    "https://nasional.sindonews.com/",
                    "https://daerah.sindonews.com/",
                    "https://metro.sindonews.com/",
                    "https://www.sindonews.com/topic/banjir",
                    "https://www.sindonews.com/topic/gempa",
                    "https://www.sindonews.com/topic/bencana",
                ],
                link_allow_patterns=[
                    r"(nasional|daerah|metro)\.sindonews\.com/(read|newsread)/\d+/",
                ],
                title_selectors=["h1", ".detail-title", ".title"],
                date_selectors=["time", ".date", ".detail-date"],
                author_selectors=[".author", ".reporter", "[rel='author']"],
                content_selectors=[".detail-desc", ".article-content", ".content", "article"],
                remove_selectors=[".baca-juga", ".related", ".ads"],
            ),
            client=client,
        )

    def get_article_links(self, keywords: Iterable[str], max_pages: int = 1, archive_days: int = 0) -> list[str]:
        return super().get_article_links(keywords, max_pages=max_pages, archive_days=archive_days)

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)
