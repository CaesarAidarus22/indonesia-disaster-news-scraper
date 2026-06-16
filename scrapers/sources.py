from __future__ import annotations

from scrapers.bnpb import BNPBScraper
from scrapers.cnnindonesia import CNNIndonesiaScraper
from scrapers.kumparan import KumparanScraper
from scrapers.liputan6 import Liputan6Scraper
from scrapers.okezone import OkezoneScraper
from scrapers.republika import RepublikaScraper
from scrapers.sindonews import SindonewsScraper
from scrapers.suara import SuaraScraper
from scrapers.tempo import TempoScraper
from scrapers.tribunnews import TribunnewsScraper
from scrapers.base import BaseNewsScraper, SourceConfig
from utils.http import HttpClient


SOURCE_CONFIGS = [
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
        archive_url_templates=[
            "https://indeks.kompas.com/?site=all&date={date}&page={page}",
        ],
        category_urls=[
            "https://nasional.kompas.com/",
            "https://regional.kompas.com/",
            "https://www.kompas.com/tag/bencana",
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
        archive_url_templates=[
            "https://news.detik.com/indeks?date={yyyymmdd}&page={page}",
        ],
        category_urls=[
            "https://news.detik.com/berita",
            "https://news.detik.com/indeks",
            "https://www.detik.com/tag/bencana",
            "https://www.detik.com/search/searchall?query=bencana&sortby=time&page={page}",
        ],
        link_allow_patterns=[r"/d-\d+/", r"/berita/"],
        title_selectors=["h1.detail__title", "h1"],
        date_selectors=[".detail__date", "time"],
        author_selectors=[".detail__author", ".author"],
        content_selectors=[".detail__body-text", "article"],
        remove_selectors=[".detail__body-tag", ".parallaxindetail"],
    ),
]


def build_scrapers(
    delay_seconds: float,
    timeout_seconds: int,
    include_antara: bool = False,
    include_bnpb: bool = False,
) -> list[BaseNewsScraper]:
    client = HttpClient(delay_seconds=delay_seconds, timeout_seconds=timeout_seconds)
    scrapers: list[BaseNewsScraper] = []
    if include_bnpb:
        scrapers.append(BNPBScraper(client=client))

    scrapers.extend(
        BaseNewsScraper(config, client=client)
        for config in SOURCE_CONFIGS
        if include_antara or config.name != "Antara News"
    )
    scrapers.extend(
        [
            CNNIndonesiaScraper(client=client),
            TempoScraper(client=client),
            RepublikaScraper(client=client),
            KumparanScraper(client=client),
            Liputan6Scraper(client=client),
            TribunnewsScraper(client=client),
            SindonewsScraper(client=client),
            SuaraScraper(client=client),
            OkezoneScraper(client=client),
        ]
    )
    return scrapers
