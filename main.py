from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from scrapers.base import BaseNewsScraper
from scrapers.sources import build_scrapers
from utils.filters import DISASTER_KEYWORDS
from utils.storage import remove_duplicate_urls, save_to_csv, save_to_json


DEFAULT_SEARCH_KEYWORDS = [
    "bencana",
    "banjir",
    "gempa bumi",
    "tsunami",
    "tanah longsor",
    "kebakaran",
    "erupsi",
    "puting beliung",
    "kekeringan",
    "abrasi",
    "gelombang tinggi",
    "kecelakaan industri",
    "evakuasi",
    "tewas",
    "mengungsi",
    "BNPB",
    "BPBD",
]


def get_article_links(
    scraper: BaseNewsScraper,
    keywords: list[str],
    max_pages: int,
    max_links: int,
) -> list[str]:
    links = scraper.get_article_links(keywords=keywords, max_pages=max_pages)
    return links[:max_links]


def parse_article(scraper: BaseNewsScraper, url: str) -> dict | None:
    return scraper.parse_article(url)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape Indonesian disaster news for NLP/NER dataset collection.",
    )
    parser.add_argument("--output-dir", default="data/raw", help="Output directory for CSV and JSON files.")
    parser.add_argument("--max-pages", type=int, default=1, help="Search page templates to use per keyword.")
    parser.add_argument("--max-links-per-source", type=int, default=25, help="Maximum article URLs parsed per source.")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between requests in seconds.")
    parser.add_argument("--timeout", type=int, default=15, help="Request timeout in seconds.")
    parser.add_argument(
        "--include-antara",
        action="store_true",
        help="Enable Antara News scraping manually. Disabled by default.",
    )
    parser.add_argument(
        "--keywords",
        nargs="*",
        default=DEFAULT_SEARCH_KEYWORDS,
        help="Search keywords. Filtering still uses the full disaster keyword list.",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    scrapers = build_scrapers(
        delay_seconds=args.delay,
        timeout_seconds=args.timeout,
        include_antara=args.include_antara,
    )
    all_links: list[tuple[BaseNewsScraper, str]] = []

    logging.info("Using %d disaster filter keywords: %s", len(DISASTER_KEYWORDS), ", ".join(DISASTER_KEYWORDS))
    for scraper in scrapers:
        logging.info("Collecting links from %s", scraper.config.name)
        links = get_article_links(
            scraper=scraper,
            keywords=args.keywords,
            max_pages=args.max_pages,
            max_links=args.max_links_per_source,
        )
        logging.info("Found %d candidate links from %s", len(links), scraper.config.name)
        all_links.extend((scraper, url) for url in links)

    records: list[dict] = []
    seen_urls: set[str] = set()
    for scraper, url in tqdm(all_links, desc="Parsing articles"):
        if url in seen_urls:
            continue
        seen_urls.add(url)
        record = parse_article(scraper, url)
        if record:
            records.append(record)

    records = remove_duplicate_urls(records)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir)
    csv_path = output_dir / f"indonesia_disaster_news_{timestamp}.csv"
    json_path = output_dir / f"indonesia_disaster_news_{timestamp}.json"

    save_to_csv(records, csv_path)
    save_to_json(records, json_path)

    logging.info("Saved %d filtered articles to %s", len(records), csv_path)
    logging.info("Saved %d filtered articles to %s", len(records), json_path)


if __name__ == "__main__":
    main()
