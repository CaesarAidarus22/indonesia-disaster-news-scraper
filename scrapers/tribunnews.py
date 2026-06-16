from __future__ import annotations

from typing import Iterable

from scrapers.base import SourceConfig
from scrapers.portal import DisasterPortalScraper


class TribunnewsScraper(DisasterPortalScraper):
    sitemap_urls = [
        "https://www.tribunnews.com/sitemap.xml",
        "https://www.tribunnews.com/regional/sitemap-news.xml",
        "https://www.tribunnews.com/regional/sitemap-web.xml",
        "https://www.tribunnews.com/nasional/sitemap-news.xml",
        "https://www.tribunnews.com/nasional/sitemap-web.xml",
        "https://www.tribunnews.com/metropolitan/sitemap-news.xml",
        "https://www.tribunnews.com/metropolitan/sitemap-web.xml",
    ]
    sitemap_allow_keywords = [
        "/regional/sitemap-news",
        "/regional/sitemap-web",
        "/nasional/sitemap-news",
        "/nasional/sitemap-web",
        "/metropolitan/sitemap-news",
        "/metropolitan/sitemap-web",
    ]

    def __init__(self, client=None) -> None:
        super().__init__(
            SourceConfig(
                name="Tribunnews.com",
                base_url="https://www.tribunnews.com/",
                search_urls=[],
                archive_url_templates=[
                    "https://www.tribunnews.com/index-news?date={date}&page={page}",
                ],
                category_urls=[
                    "https://www.tribunnews.com/nasional",
                    "https://www.tribunnews.com/regional",
                    "https://www.tribunnews.com/metropolitan",
                    "https://www.tribunnews.com/tag/bencana",
                    "https://www.tribunnews.com/tag/banjir",
                    "https://www.tribunnews.com/tag/gempa-bumi",
                    "https://www.tribunnews.com/tag/kebakaran",
                ],
                link_allow_patterns=[
                    r"tribunnews\.com/(nasional|regional|metropolitan|tribunners|tribunnews)/(\d{4}/\d{2}/\d{2}/|\d+/)",
                    r"[a-z0-9-]+\.tribunnews\.com/\d{4}/\d{2}/\d{2}/",
                ],
                title_selectors=["h1", ".f50", ".title"],
                date_selectors=["time", ".grey", ".date"],
                author_selectors=[".reporter", ".editor", ".author"],
                content_selectors=[".txt-article", ".article", "article"],
                remove_selectors=[".baca", ".readalso", ".ads", ".side-article"],
            ),
            client=client,
        )

    def get_article_links(self, keywords: Iterable[str], max_pages: int = 1, archive_days: int = 0) -> list[str]:
        return super().get_article_links(keywords, max_pages=max_pages, archive_days=archive_days)

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)
