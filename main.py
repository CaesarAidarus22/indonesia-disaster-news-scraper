from __future__ import annotations

import argparse
import logging
import re
from difflib import SequenceMatcher
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
    "kebakaran hutan",
    "karhutla",
    "erupsi",
    "gunung meletus",
    "puting beliung",
    "kekeringan",
    "abrasi",
    "gelombang tinggi",
    "kecelakaan industri",
    "evakuasi",
    "korban jiwa",
    "bantuan logistik",
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
    archive_days: int,
) -> list[str]:
    links = scraper.get_article_links(
        keywords=keywords,
        max_pages=max_pages,
        archive_days=archive_days,
    )
    return links[:max_links]


def parse_article(scraper: BaseNewsScraper, url: str) -> dict | None:
    return scraper.parse_article(url)


SOURCE_SUMMARY_ORDER = [
    "Kompas.com",
    "Detik.com",
    "Tempo.co",
    "Republika.co.id",
    "Kumparan.com",
    "Liputan6.com",
    "CNNIndonesia.com",
    "Tribunnews.com",
    "Sindonews.com",
    "Suara.com",
    "Okezone.com",
    "Antara News",
    "BNPB.go.id",
]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape Indonesian disaster news for NLP/NER dataset collection.",
    )
    parser.add_argument("--output-dir", default="data/raw", help="Output directory for CSV and JSON files.")
    parser.add_argument("--max-pages", type=int, default=1, help="Search page templates to use per keyword.")
    parser.add_argument("--max-links-per-source", type=int, default=25, help="Maximum article URLs parsed per source.")
    parser.add_argument(
        "--archive-days",
        type=int,
        default=0,
        help="Try archive crawling for the last N days, for example --archive-days 365.",
    )
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between requests in seconds.")
    parser.add_argument("--timeout", type=int, default=15, help="Request timeout in seconds.")
    parser.add_argument(
        "--include-antara",
        action="store_true",
        help="Enable Antara News scraping manually. Disabled by default.",
    )
    parser.add_argument(
        "--include-bnpb",
        action="store_true",
        help="Enable BNPB.go.id scraping manually. Disabled by default because its search endpoint can return 500.",
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
        include_bnpb=args.include_bnpb,
    )
    all_links: list[tuple[BaseNewsScraper, str]] = []
    global_seen_urls: set[str] = set()
    global_duplicate_urls_skipped = 0
    source_stats: dict[str, dict[str, int]] = {}
    seen_titles: set[str] = set()
    seen_title_fingerprints: list[str] = []

    logging.info("Using %d disaster filter keywords: %s", len(DISASTER_KEYWORDS), ", ".join(DISASTER_KEYWORDS))
    for scraper in scrapers:
        logging.info("Collecting links from %s", scraper.config.name)
        candidate_links = get_article_links(
            scraper=scraper,
            keywords=args.keywords,
            max_pages=args.max_pages,
            max_links=args.max_links_per_source,
            archive_days=args.archive_days,
        )
        unique_links: list[str] = []
        for url in candidate_links:
            if url in global_seen_urls:
                global_duplicate_urls_skipped += 1
                continue
            global_seen_urls.add(url)
            unique_links.append(url)

        source_stats.setdefault(scraper.config.name, {"candidate": 0, "parsed": 0, "accepted": 0, "rejected": 0})
        source_stats[scraper.config.name]["candidate"] += len(unique_links)

        logging.info(
            (
                "Collecting links from %s complete: "
                "unique_urls_found=%d duplicate_urls_skipped=%d "
                "archive_urls_found=%d archive_urls_skipped=%d archive_urls_after_filter=%d "
                "sitemap_urls_found=%d category_urls_found=%d "
                "article_urls_before_filter=%d article_urls_after_filter=%d "
                "global_duplicates_skipped=%d"
            ),
            scraper.config.name,
            scraper.unique_urls_found,
            scraper.duplicate_urls_skipped,
            scraper.archive_urls_found,
            scraper.archive_urls_skipped,
            scraper.archive_urls_after_filter,
            scraper.sitemap_urls_found,
            scraper.category_urls_found,
            scraper.article_urls_before_filter,
            scraper.article_urls_after_filter,
            global_duplicate_urls_skipped,
        )
        logging.info("Found %d sitemap URLs from %s", scraper.sitemap_urls_found, scraper.config.name)
        logging.info("Found %d category URLs from %s", scraper.category_urls_found, scraper.config.name)
        logging.info("Found %d article URLs before filter from %s", scraper.article_urls_before_filter, scraper.config.name)
        logging.info("Found %d article URLs after filter from %s", scraper.article_urls_after_filter, scraper.config.name)
        logging.info("Found %d unique candidate links from %s", len(unique_links), scraper.config.name)
        if scraper.config.name == "Liputan6.com":
            logging.info("Found %d candidate links from Liputan6.com", len(unique_links))
        all_links.extend((scraper, url) for url in unique_links)

    records: list[dict] = []
    seen_urls: set[str] = set()
    for scraper, url in tqdm(all_links, desc="Parsing articles"):
        if url in seen_urls:
            continue
        seen_urls.add(url)
        source_stats.setdefault(scraper.config.name, {"candidate": 0, "parsed": 0, "accepted": 0, "rejected": 0})
        source_stats[scraper.config.name]["parsed"] += 1
        record = parse_article(scraper, url)
        if not record:
            source_stats[scraper.config.name]["rejected"] += 1
            continue

        title_key = normalize_title_for_dedup(record.get("title", ""))
        title_fingerprint = title_near_duplicate_fingerprint(record.get("title", ""))
        if is_duplicate_title(title_key, title_fingerprint, seen_titles, seen_title_fingerprints):
            source_stats[scraper.config.name]["rejected"] += 1
            logging.info("Skipping duplicate or near-duplicate title: %s", record.get("title", ""))
            continue

        seen_titles.add(title_key)
        seen_title_fingerprints.append(title_fingerprint)
        source_stats[scraper.config.name]["accepted"] += 1
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
    if "Liputan6.com" in source_stats:
        liputan6_stats = source_stats["Liputan6.com"]
        logging.info("Parsed %d articles from Liputan6.com", liputan6_stats["parsed"])
        print(f"Liputan6 candidate links: {liputan6_stats['candidate']}")
        print(f"Liputan6 parsed articles: {liputan6_stats['parsed']}")
        print(f"Liputan6 accepted articles: {liputan6_stats['accepted']}")
    log_source_summary(source_stats)


def normalize_title_for_dedup(title: str) -> str:
    normalized = re.sub(r"[^\w\s]", " ", title.casefold())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def title_near_duplicate_fingerprint(title: str) -> str:
    normalized = normalize_title_for_dedup(title)
    stopwords = {
        "di",
        "ke",
        "dari",
        "dan",
        "yang",
        "ini",
        "itu",
        "dalam",
        "untuk",
        "akibat",
        "karena",
        "usai",
        "hingga",
    }
    tokens = [token for token in normalized.split() if token not in stopwords]
    return " ".join(tokens[:14])


def is_duplicate_title(
    title_key: str,
    title_fingerprint: str,
    seen_titles: set[str],
    seen_title_fingerprints: list[str],
) -> bool:
    if not title_key:
        return True
    if title_key in seen_titles:
        return True
    for seen_fingerprint in seen_title_fingerprints:
        if not seen_fingerprint:
            continue
        if SequenceMatcher(None, title_fingerprint, seen_fingerprint).ratio() >= 0.92:
            return True
    return False


def log_source_summary(source_stats: dict[str, dict[str, int]]) -> None:
    logging.info("## Source Summary")
    print("## Source Summary")
    for source in SOURCE_SUMMARY_ORDER:
        stats = source_stats.get(source, {"candidate": 0, "parsed": 0, "accepted": 0, "rejected": 0})
        line = (
            f"{source}: Found {stats.get('candidate', 0)} candidate links, "
            f"Parsed {stats.get('parsed', 0)} articles, "
            f"Accepted {stats.get('accepted', 0)} articles, "
            f"Rejected {stats.get('rejected', 0)} articles"
        )
        logging.info(line)
        print(line)


if __name__ == "__main__":
    main()
