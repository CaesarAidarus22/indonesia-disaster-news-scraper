from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from scrapers.base import BaseNewsScraper, SourceConfig
from utils.text import clean_text


class SitemapFirstNewsScraper(BaseNewsScraper):
    sitemap_urls: list[str] = []
    category_urls: list[str] = []

    def __init__(self, config: SourceConfig, client=None) -> None:
        super().__init__(config=config, client=client)

    def get_article_links(
        self,
        keywords: Iterable[str],
        max_pages: int = 1,
        archive_days: int = 0,
    ) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()
        self.unique_urls_found = 0
        self.duplicate_urls_skipped = 0
        self.archive_urls_found = 0
        self.archive_urls_skipped = 0
        self.archive_urls_after_filter = 0

        self._collect_from_sitemaps(links, seen, max_pages=max_pages, archive_days=archive_days)
        if not links:
            logging.info("No sitemap links found for %s, falling back to category pages", self.config.name)
            self._collect_from_categories(keywords, links, seen, max_pages=max_pages)

        self.unique_urls_found = len(seen)
        return links

    def parse_article(self, url: str) -> dict | None:
        return super().parse_article(url)

    def _collect_from_sitemaps(
        self,
        links: list[str],
        seen: set[str],
        max_pages: int,
        archive_days: int,
    ) -> None:
        sitemap_queue = self.sitemap_urls[:max_pages]
        processed = 0
        max_sitemaps = max(1, max_pages) * 8
        cutoff = self._archive_cutoff(archive_days)

        while sitemap_queue and processed < max_sitemaps:
            sitemap_url = sitemap_queue.pop(0)
            processed += 1
            if not self.client.can_fetch(sitemap_url):
                logging.info("Skipping disallowed sitemap by robots.txt: %s", sitemap_url)
                continue

            html = self.client.get(sitemap_url)
            if not html:
                continue

            soup = BeautifulSoup(html, "xml")
            child_sitemaps = [loc.get_text(strip=True) for loc in soup.select("sitemap loc")]
            if child_sitemaps:
                sitemap_queue.extend(child_sitemaps[:max_pages])
                continue

            for url_node in soup.select("url"):
                loc = url_node.select_one("loc")
                if not loc:
                    continue
                if cutoff and not self._is_recent_sitemap_url(url_node, cutoff):
                    continue
                url = self._normalize_url(loc.get_text(strip=True))
                if url:
                    self.archive_urls_found += 1
                if not url or url in seen:
                    if url:
                        self.duplicate_urls_skipped += 1
                        self.archive_urls_skipped += 1
                    continue
                if not self.client.can_fetch(url):
                    logging.info("Skipping disallowed article link by robots.txt: %s", url)
                    self.archive_urls_skipped += 1
                    continue
                if not self._passes_url_prefilter(url):
                    self.archive_urls_skipped += 1
                    continue
                if self._looks_like_article_url(url, "", require_article_hint=True):
                    seen.add(url)
                    links.append(url)
                    self.archive_urls_after_filter += 1
                else:
                    self.archive_urls_skipped += 1

    def _collect_from_categories(
        self,
        keywords: Iterable[str],
        links: list[str],
        seen: set[str],
        max_pages: int,
    ) -> None:
        for category_url in self.category_urls:
            for page in range(1, max_pages + 1):
                category_page_url = self._format_page_url(category_url, page)
                if not self.client.can_fetch(category_page_url):
                    logging.info("Skipping disallowed category by robots.txt: %s", category_page_url)
                    continue

                html = self.client.get(category_page_url)
                if not html:
                    continue

                soup = BeautifulSoup(html, "lxml")
                for anchor in soup.find_all("a", href=True):
                    url = self._normalize_url(anchor.get("href"))
                    if not url or url in seen:
                        if url:
                            self.duplicate_urls_skipped += 1
                        continue
                    if not self.client.can_fetch(url):
                        logging.info("Skipping disallowed article link by robots.txt: %s", url)
                        continue
                    anchor_text = clean_text(anchor.get_text(" "))
                    if not self._passes_url_prefilter(url, anchor_text, context_text=category_page_url):
                        continue
                    if self._looks_like_article_url(
                        url,
                        anchor_text,
                        require_article_hint=not self._is_disaster_context(category_page_url),
                    ):
                        seen.add(url)
                        links.append(url)

    def _matches_keyword(self, text: str, keywords: Iterable[str]) -> bool:
        normalized = re.sub(r"[-_+%20]+", " ", text.casefold())
        for keyword in keywords:
            normalized_keyword = re.sub(r"\s+", " ", keyword.casefold()).strip()
            if re.search(rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)", normalized):
                return True
        return False

    def _archive_cutoff(self, archive_days: int) -> datetime | None:
        if archive_days <= 0:
            return None
        return datetime.now(timezone.utc) - timedelta(days=archive_days)

    def _is_recent_sitemap_url(self, url_node, cutoff: datetime) -> bool:
        lastmod = url_node.select_one("lastmod")
        if not lastmod:
            return True
        try:
            parsed = date_parser.parse(lastmod.get_text(strip=True))
            if not parsed.tzinfo:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed >= cutoff
        except (ValueError, TypeError, OverflowError):
            return True
