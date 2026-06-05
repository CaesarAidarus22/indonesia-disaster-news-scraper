from __future__ import annotations

from scrapers.kumparan import KumparanScraper
from scrapers.republika import RepublikaScraper
from scrapers.tempo import TempoScraper
from scrapers.base import BaseNewsScraper, SourceConfig
from utils.http import HttpClient


SOURCE_CONFIGS = [
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
    SourceConfig(
        name="Antara News",
        base_url="https://www.antaranews.com/",
        search_urls=[
            "https://www.antaranews.com/search?q={query}",
        ],
        link_allow_patterns=[r"/berita/\d+/"],
        title_selectors=["h1", ".post-title"],
        date_selectors=["time", ".text-muted", ".post-date"],
        author_selectors=[".post-author", ".author"],
        content_selectors=["article .post-content", ".post-content", "article"],
        remove_selectors=[".baca-juga", ".adsbygoogle"],
    ),
    SourceConfig(
        name="Kompas.com",
        base_url="https://www.kompas.com/",
        search_urls=[
            "https://search.kompas.com/search/?q={query}",
        ],
        link_allow_patterns=[r"/read/\d+/"],
        title_selectors=["h1.read__title", "h1", ".read__title"],
        date_selectors=[".read__time", "time"],
        author_selectors=[".read__author", ".credit-title-name", ".author"],
        content_selectors=[".read__content", "article"],
        remove_selectors=[".read__credit", ".ads-on-paragraph"],
    ),
    SourceConfig(
        name="Detik.com",
        base_url="https://www.detik.com/",
        search_urls=[
            "https://www.detik.com/search/searchall?query={query}",
        ],
        link_allow_patterns=[r"/d-\d+/", r"/berita/"],
        title_selectors=["h1.detail__title", "h1"],
        date_selectors=[".detail__date", "time"],
        author_selectors=[".detail__author", ".author"],
        content_selectors=[".detail__body-text", "article"],
        remove_selectors=[".detail__body-tag", ".parallaxindetail"],
    ),
    SourceConfig(
        name="CNNIndonesia.com",
        base_url="https://www.cnnindonesia.com/",
        search_urls=[
            "https://www.cnnindonesia.com/search/?query={query}",
        ],
        link_allow_patterns=[r"/\d{8,}/"],
        title_selectors=["h1", ".title"],
        date_selectors=[".text-cnn_grey", "time"],
        author_selectors=[".author", ".detail-author"],
        content_selectors=[".detail-text", "article"],
        remove_selectors=[".paradetail", ".video"],
    ),
]


def build_scrapers(
    delay_seconds: float,
    timeout_seconds: int,
    include_antara: bool = False,
) -> list[BaseNewsScraper]:
    client = HttpClient(delay_seconds=delay_seconds, timeout_seconds=timeout_seconds)
    scrapers: list[BaseNewsScraper] = [
        BaseNewsScraper(config, client=client)
        for config in SOURCE_CONFIGS
        if include_antara or config.name != "Antara News"
    ]
    scrapers.extend(
        [
            TempoScraper(client=client),
            RepublikaScraper(client=client),
            KumparanScraper(client=client),
        ]
    )
    return scrapers
