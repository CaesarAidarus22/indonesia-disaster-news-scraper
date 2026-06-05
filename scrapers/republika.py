from __future__ import annotations

from typing import Iterable

from scrapers.base import SourceConfig
from scrapers.sitemap import SitemapFirstNewsScraper


class RepublikaScraper(SitemapFirstNewsScraper):
    sitemap_urls = [
        "https://www.republika.co.id/sitemap.xml",
        "https://www.republika.co.id/sitemap-news.xml",
    ]
    category_urls = [
        "https://www.republika.co.id/kanal/news/nasional",
        "https://www.republika.co.id/kanal/news/regional",
        "https://www.republika.co.id/tag/bencana",
    ]

    def __init__(self, client=None) -> None:
        super().__init__(
            SourceConfig(
                name="Republika.co.id",
                base_url="https://www.republika.co.id/",
                search_urls=[],
                link_allow_patterns=[r"republika\.co\.id/berita/"],
                title_selectors=["h1", ".article-title", ".title"],
                date_selectors=["time", ".date", ".article-date"],
                author_selectors=[".author", ".article-author", "[rel='author']"],
                content_selectors=["article", ".article-content", ".detail-content", ".content-detail"],
                remove_selectors=[".baca-juga", ".related", ".ads"],
            ),
            client=client,
        )

    def get_article_links(self, keywords: Iterable[str], max_pages: int = 1) -> list[str]:
        return super().get_article_links(keywords=keywords, max_pages=max_pages)

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)
