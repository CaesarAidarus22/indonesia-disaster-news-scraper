from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from utils.filters import (
    get_actual_disaster_event_result,
    has_strong_foreign_signal,
    has_specific_indonesia_location,
    is_disaster_article,
    is_indonesia_related_article,
)
from utils.http import HttpClient
from utils.text import clean_text


BLOCKED_URL_KEYWORDS = [
    "/topik/",
    "/pandangan/",
    "/opini/",
    "/cekfakta/",
    "/cek-fakta/",
    "/gaya-hidup/",
    "/gaya_hidup/",
    "/lifestyle/",
    "/tekno/",
    "/technology/",
    "/gadget/",
    "/selebriti/",
    "/celebrity/",
    "/travel/",
    "/internasional/",
    "/international/",
    "/luar-negeri/",
    "/luar_negeri/",
    "/otomotif/",
    "/properti/",
    "/property/",
    "/hiburan/",
    "/entertainment/",
    "/bola/",
    "/sport/",
    "/sports/",
    "/zodiak/",
    "/feature/",
]


FOCUS_URL_KEYWORDS = [
    "nasional",
    "regional",
    "peristiwa",
    "news",
    "berita",
    "bencana",
    "lingkungan",
    "metro",
    "daerah",
]


@dataclass(frozen=True)
class SourceConfig:
    name: str
    base_url: str
    search_urls: list[str]
    archive_url_templates: list[str] = field(default_factory=list)
    category_urls: list[str] = field(default_factory=list)
    link_allow_patterns: list[str] = field(default_factory=list)
    title_selectors: list[str] = field(default_factory=list)
    date_selectors: list[str] = field(default_factory=list)
    author_selectors: list[str] = field(default_factory=list)
    content_selectors: list[str] = field(default_factory=list)
    remove_selectors: list[str] = field(default_factory=list)


class BaseNewsScraper:
    def __init__(self, config: SourceConfig, client: HttpClient | None = None) -> None:
        self.config = config
        self.client = client or HttpClient()
        self.netloc = urlparse(config.base_url).netloc.replace("www.", "")
        self.unique_urls_found = 0
        self.duplicate_urls_skipped = 0
        self.archive_urls_found = 0
        self.archive_urls_skipped = 0
        self.archive_urls_after_filter = 0
        self.sitemap_urls_found = 0
        self.category_urls_found = 0
        self.article_urls_before_filter = 0
        self.article_urls_after_filter = 0

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
        self.sitemap_urls_found = 0
        self.category_urls_found = 0
        self.article_urls_before_filter = 0
        self.article_urls_after_filter = 0

        self._collect_from_archive_pages(links, seen, max_pages=max_pages, archive_days=archive_days)
        self._collect_from_category_pages(links, seen, max_pages=max_pages)
        self._collect_from_search_pages(links, seen, keywords=keywords, max_pages=max_pages)

        self.unique_urls_found = len(seen)
        return links

    def _collect_from_search_pages(
        self,
        links: list[str],
        seen: set[str],
        keywords: Iterable[str],
        max_pages: int,
    ) -> None:
        for keyword in keywords:
            for url_template in self.config.search_urls[:max_pages]:
                search_url = url_template.format(query=keyword.replace(" ", "+"))
                if not self.client.can_fetch(search_url):
                    logging.info("Skipping disallowed URL by robots.txt: %s", search_url)
                    continue
                html = self.client.get(search_url)
                if not html:
                    continue

                soup = BeautifulSoup(html, "lxml")
                self._collect_links_from_soup(soup, links, seen, require_article_hint=True)

    def _collect_from_archive_pages(
        self,
        links: list[str],
        seen: set[str],
        max_pages: int,
        archive_days: int,
    ) -> None:
        if archive_days <= 0 or not self.config.archive_url_templates:
            return

        for archive_date in self._iter_archive_dates(archive_days):
            for url_template in self.config.archive_url_templates:
                for page in range(1, max_pages + 1):
                    archive_url = self._format_archive_url(url_template, archive_date, page)
                    if not self.client.can_fetch(archive_url):
                        logging.info("Skipping disallowed archive by robots.txt: %s", archive_url)
                        continue
                    html = self.client.get(archive_url)
                    if not html:
                        continue

                    soup = BeautifulSoup(html, "lxml")
                    self._collect_links_from_soup(
                        soup,
                        links,
                        seen,
                        require_article_hint=True,
                        context_text=archive_url,
                        count_archive_stats=True,
                    )

    def _collect_from_category_pages(
        self,
        links: list[str],
        seen: set[str],
        max_pages: int,
    ) -> None:
        for category_url in self.config.category_urls:
            for page in range(1, max_pages + 1):
                url = self._format_page_url(category_url, page)
                self.category_urls_found += 1
                if not self.client.can_fetch(url):
                    logging.info("Skipping disallowed category by robots.txt: %s", url)
                    continue
                html = self.client.get(url)
                if not html:
                    continue

                soup = BeautifulSoup(html, "lxml")
                self._collect_links_from_soup(
                    soup,
                    links,
                    seen,
                    require_article_hint=not self._is_disaster_context(url),
                    context_text=url,
                )

    def _collect_links_from_soup(
        self,
        soup: BeautifulSoup,
        links: list[str],
        seen: set[str],
        require_article_hint: bool,
        context_text: str = "",
        count_archive_stats: bool = False,
    ) -> None:
        for anchor in soup.find_all("a", href=True):
            url = self._normalize_url(anchor.get("href"))
            if not url:
                continue
            self.article_urls_before_filter += 1
            if count_archive_stats:
                self.archive_urls_found += 1
            if url in seen:
                self.duplicate_urls_skipped += 1
                if count_archive_stats:
                    self.archive_urls_skipped += 1
                continue
            if not self.client.can_fetch(url):
                logging.info("Skipping disallowed article link by robots.txt: %s", url)
                if count_archive_stats:
                    self.archive_urls_skipped += 1
                continue
            anchor_text = clean_text(anchor.get_text(" "))
            if not self._passes_url_prefilter(url, anchor_text, context_text=context_text):
                if count_archive_stats:
                    self.archive_urls_skipped += 1
                continue
            if self._looks_like_article_url(url, anchor_text, require_article_hint=require_article_hint):
                seen.add(url)
                links.append(url)
                self.article_urls_after_filter += 1
                if count_archive_stats:
                    self.archive_urls_after_filter += 1
            elif count_archive_stats:
                self.archive_urls_skipped += 1

    def parse_article(self, url: str) -> dict | None:
        if not self.client.can_fetch(url):
            logging.info("Skipping disallowed article by robots.txt: %s", url)
            return None

        html = self.client.get(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        self._remove_noise(soup)

        title = self._extract_title(soup)
        content = self._extract_content(soup)
        if not title or not content:
            logging.warning("Empty article fields for %s", url)
            return None

        full_text = f"{title} {content}"
        disaster = is_disaster_article(full_text)
        indonesia = is_indonesia_related_article(full_text)
        if not (disaster.passed and indonesia.passed):
            return None
        if has_strong_foreign_signal(full_text) and not has_specific_indonesia_location(indonesia.found_keywords):
            return None
        event = get_actual_disaster_event_result(full_text)
        if not event.passed:
            logging.info("Rejected non-event article %s: %s", url, event.rejection_reason)
            return None

        return {
            "id": self._make_id(url),
            "title": title,
            "url": url,
            "source": self.config.name,
            "published_date": self._extract_date(soup),
            "author": self._extract_author(soup),
            "content": content,
            "disaster_keywords_found": ", ".join(disaster.found_keywords),
            "indonesia_location_keywords_found": ", ".join(indonesia.found_keywords),
            "event_score": event.event_score,
            "rejection_reason": "",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

    def _normalize_url(self, href: str | None) -> str | None:
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            return None
        url = urljoin(self.config.base_url, href)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return None
        if self.netloc not in parsed.netloc.replace("www.", ""):
            return None
        return parsed._replace(fragment="", query=parsed.query).geturl()

    def _looks_like_article_url(
        self,
        url: str,
        anchor_text: str,
        require_article_hint: bool = True,
    ) -> bool:
        if self.config.link_allow_patterns:
            if not any(re.search(pattern, url, re.IGNORECASE) for pattern in self.config.link_allow_patterns):
                return False

        text = f"{url} {anchor_text}".casefold()
        negative_paths = ["/tag/", "/tags/", "/search", "/indeks", "/video/", "/foto/", *BLOCKED_URL_KEYWORDS]
        if any(path in text for path in negative_paths):
            return False

        article_hint_tokens = [
            "bencana",
            "banjir",
            "gempa",
            "longsor",
            "kebakaran",
            "bnpb",
            "bpbd",
            "bmkg",
            "cuaca ekstrem",
            "hujan lebat",
            "hujan deras",
            "erupsi",
            "tsunami",
            "evakuasi",
            "tewas",
            "meninggal",
            "mengungsi",
            "terdampak",
            "hanyut",
            "rusak",
        ]
        return not require_article_hint or any(token in text for token in article_hint_tokens)

    def _passes_url_prefilter(self, url: str, anchor_text: str = "", context_text: str = "") -> bool:
        text = f"{url} {anchor_text} {context_text}".casefold()
        normalized_text = text.replace("_", "-")
        if any(blocked in normalized_text for blocked in BLOCKED_URL_KEYWORDS):
            return False

        has_focus = any(keyword in normalized_text for keyword in FOCUS_URL_KEYWORDS)
        if has_focus:
            return True

        disaster_hint_tokens = [
            "bencana",
            "banjir",
            "gempa",
            "longsor",
            "kebakaran",
            "erupsi",
            "tsunami",
            "evakuasi",
            "mengungsi",
            "tewas",
            "meninggal",
            "terdampak",
            "bpbd",
            "bnpb",
            "bmkg",
            "cuaca ekstrem",
            "hujan lebat",
            "hujan deras",
        ]
        return any(token in normalized_text for token in disaster_hint_tokens)

    def _is_disaster_context(self, text: str) -> bool:
        normalized_text = text.casefold()
        return any(
            token in normalized_text
            for token in [
                "bencana",
                "banjir",
                "gempa",
                "longsor",
                "kebakaran",
                "erupsi",
                "tsunami",
            ]
        )

    def _iter_archive_dates(self, archive_days: int) -> Iterable[date]:
        today = datetime.now().date()
        for offset in range(max(archive_days, 0)):
            yield today - timedelta(days=offset)

    def _format_archive_url(self, url_template: str, archive_date: date, page: int) -> str:
        return url_template.format(
            date=archive_date.isoformat(),
            yyyymmdd=archive_date.strftime("%Y%m%d"),
            year=archive_date.year,
            month=f"{archive_date.month:02d}",
            day=f"{archive_date.day:02d}",
            page=page,
        )

    def _format_page_url(self, url: str, page: int) -> str:
        if "{page}" in url:
            return url.format(page=page)
        if page <= 1:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}page={page}"

    def _keyword_slug(self, keyword: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", keyword.casefold())
        slug = re.sub(r"\s+", "-", slug.strip())
        return slug

    def _remove_noise(self, soup: BeautifulSoup) -> None:
        selectors = [
            "script",
            "style",
            "noscript",
            "iframe",
            "form",
            "nav",
            "footer",
            ".ads",
            ".advertisement",
            ".related",
            ".tag",
            ".share",
            *self.config.remove_selectors,
        ]
        for selector in selectors:
            for element in soup.select(selector):
                element.decompose()

    def _extract_title(self, soup: BeautifulSoup) -> str:
        for selector in self.config.title_selectors:
            element = soup.select_one(selector)
            if element:
                text = clean_text(element.get_text(" "))
                if text:
                    return text
        meta = soup.select_one("meta[property='og:title'], meta[name='twitter:title']")
        return clean_text(meta.get("content", "")) if meta else ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        paragraphs: list[str] = []
        for selector in self.config.content_selectors:
            container = soup.select_one(selector)
            if not container:
                continue
            for paragraph in container.find_all(["p", "li"]):
                text = clean_text(paragraph.get_text(" "))
                if self._is_useful_paragraph(text):
                    paragraphs.append(text)
            if paragraphs:
                return clean_text(" ".join(paragraphs))

        for paragraph in soup.find_all("p"):
            text = clean_text(paragraph.get_text(" "))
            if self._is_useful_paragraph(text):
                paragraphs.append(text)
        return clean_text(" ".join(paragraphs))

    def _extract_date(self, soup: BeautifulSoup) -> str:
        candidates: list[str] = []
        meta_selectors = [
            "meta[property='article:published_time']",
            "meta[name='pubdate']",
            "meta[name='publishdate']",
            "meta[name='date']",
        ]
        for selector in meta_selectors:
            meta = soup.select_one(selector)
            if meta and meta.get("content"):
                candidates.append(meta["content"])

        for selector in self.config.date_selectors:
            element = soup.select_one(selector)
            if element:
                candidates.append(element.get("datetime") or element.get_text(" "))

        json_ld_date = self._extract_json_ld_field(soup, "datePublished")
        if json_ld_date:
            candidates.append(json_ld_date)

        for candidate in candidates:
            parsed = self._parse_date(candidate)
            if parsed:
                return parsed
        return ""

    def _extract_author(self, soup: BeautifulSoup) -> str:
        meta = soup.select_one("meta[name='author'], meta[property='article:author']")
        if meta and meta.get("content"):
            return clean_text(meta["content"])

        for selector in self.config.author_selectors:
            element = soup.select_one(selector)
            if element:
                author = clean_text(element.get_text(" "))
                if author:
                    return author

        json_ld_author = self._extract_json_ld_author(soup)
        return clean_text(json_ld_author)

    def _extract_json_ld_field(self, soup: BeautifulSoup, field: str) -> str:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
            except json.JSONDecodeError:
                continue
            for item in self._flatten_json_ld(data):
                value = item.get(field)
                if isinstance(value, str):
                    return value
        return ""

    def _extract_json_ld_author(self, soup: BeautifulSoup) -> str:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
            except json.JSONDecodeError:
                continue
            for item in self._flatten_json_ld(data):
                author = item.get("author")
                if isinstance(author, dict):
                    return str(author.get("name", ""))
                if isinstance(author, list) and author:
                    first = author[0]
                    if isinstance(first, dict):
                        return str(first.get("name", ""))
                if isinstance(author, str):
                    return author
        return ""

    def _flatten_json_ld(self, data: object) -> list[dict]:
        if isinstance(data, dict):
            graph = data.get("@graph")
            if isinstance(graph, list):
                return [item for item in graph if isinstance(item, dict)] + [data]
            return [data]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    def _parse_date(self, raw_date: str) -> str:
        cleaned = clean_text(raw_date)
        if not cleaned:
            return ""
        try:
            return date_parser.parse(cleaned, fuzzy=True).isoformat()
        except (ValueError, TypeError, OverflowError):
            return cleaned

    def _is_useful_paragraph(self, text: str) -> bool:
        lowered = text.casefold()
        blocked = [
            "baca juga",
            "simak juga",
            "download aplikasi",
            "ikuti berita",
            "copyright",
            "editor:",
            "penulis:",
        ]
        return len(text) >= 40 and not any(item in lowered for item in blocked)

    def _make_id(self, url: str) -> str:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
        return f"{self.config.name.lower().replace(' ', '_')}_{digest}"
