from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from utils.text import normalize_for_match


DISASTER_KEYWORDS = [
    "banjir",
    "gempa",
    "gempa bumi",
    "tsunami",
    "longsor",
    "tanah longsor",
    "kebakaran",
    "erupsi",
    "gunung meletus",
    "puting beliung",
    "kekeringan",
    "abrasi",
    "gelombang tinggi",
    "korban jiwa",
    "pengungsi",
    "evakuasi",
    "kerusakan",
    "bantuan logistik",
    "bnpb",
    "bpbd",
]


INDONESIA_LOCATION_KEYWORDS = [
    "indonesia",
    "ri",
    "aceh",
    "sumatera",
    "sumut",
    "sumbar",
    "riau",
    "jambi",
    "bengkulu",
    "lampung",
    "bangka belitung",
    "kepulauan riau",
    "jakarta",
    "jawa barat",
    "jawa tengah",
    "jawa timur",
    "banten",
    "yogyakarta",
    "bali",
    "ntb",
    "nusa tenggara barat",
    "ntt",
    "nusa tenggara timur",
    "kalimantan",
    "sulawesi",
    "maluku",
    "papua",
    "banda aceh",
    "medan",
    "padang",
    "pekanbaru",
    "palembang",
    "bandung",
    "semarang",
    "surabaya",
    "denpasar",
    "mataram",
    "kupang",
    "pontianak",
    "banjarmasin",
    "samarinda",
    "balikpapan",
    "makassar",
    "manado",
    "ambon",
    "jayapura",
    "kabupaten",
    "kab.",
    "kota",
    "provinsi",
    "bpbd",
    "bnpb",
]


NEGATIVE_FOREIGN_HINTS = [
    "amerika serikat",
    "jepang",
    "china",
    "tiongkok",
    "korea",
    "india",
    "pakistan",
    "afghanistan",
    "turki",
    "suriah",
    "iran",
    "irak",
    "rusia",
    "ukraina",
    "eropa",
    "afrika",
    "australia",
    "selandia baru",
    "filipina",
    "malaysia",
    "thailand",
    "vietnam",
    "myanmar",
    "nepal",
]


EVENT_KEYWORDS = [
    "terjadi",
    "melanda",
    "mengguncang",
    "merendam",
    "terdampak",
    "tewas",
    "meninggal",
    "rusak",
    "mengungsi",
    "evakuasi",
    "jebol",
    "hanyut",
]


NON_EVENT_KEYWORDS = [
    "penelitian",
    "riset",
    "studi",
    "sejarah",
    "purba",
    "mitigasi",
    "pencegahan",
    "sosialisasi",
    "revitalisasi",
    "normalisasi",
    "pembangunan",
    "perencanaan",
    "rapat",
    "koordinasi",
    "pelatihan",
    "simulasi",
    "monitoring",
    "pos pantau",
    "sistem peringatan dini",
    "evaluasi",
    "anggaran",
    "proyek",
    "proyek infrastruktur",
    "edukasi",
    "geologi",
    "geologis",
]


STRONG_IMPACT_KEYWORDS = [
    "tewas",
    "meninggal",
    "mengungsi",
    "evakuasi",
    "rusak",
    "jebol",
    "hanyut",
    "terdampak",
]


@dataclass(frozen=True)
class FilterResult:
    passed: bool
    found_keywords: list[str]


@dataclass(frozen=True)
class EventFilterResult:
    passed: bool
    event_score: int
    event_keywords_found: list[str]
    non_event_keywords_found: list[str]
    rejection_reason: str = ""


def find_keywords(text: str, keywords: Iterable[str]) -> list[str]:
    normalized = normalize_for_match(text)
    found: list[str] = []
    for keyword in keywords:
        needle = re.escape(normalize_for_match(keyword))
        if re.search(rf"(?<!\w){needle}(?!\w)", normalized):
            found.append(keyword)
    return sorted(set(found), key=str.casefold)


def is_disaster_article(text: str) -> FilterResult:
    found = find_keywords(text, DISASTER_KEYWORDS)
    return FilterResult(passed=bool(found), found_keywords=found)


def is_indonesia_related_article(text: str) -> FilterResult:
    found = find_keywords(text, INDONESIA_LOCATION_KEYWORDS)
    return FilterResult(passed=bool(found), found_keywords=found)


def get_actual_disaster_event_result(article_text: str) -> EventFilterResult:
    event_found = find_keywords(article_text, EVENT_KEYWORDS)
    non_event_found = find_keywords(article_text, NON_EVENT_KEYWORDS)
    impact_found = find_keywords(article_text, STRONG_IMPACT_KEYWORDS)

    event_score = len(event_found) + len(impact_found)
    non_event_score = len(non_event_found)

    if not event_found:
        return EventFilterResult(
            passed=False,
            event_score=event_score,
            event_keywords_found=event_found,
            non_event_keywords_found=non_event_found,
            rejection_reason="no_event_keyword",
        )

    if non_event_score >= event_score:
        return EventFilterResult(
            passed=False,
            event_score=event_score,
            event_keywords_found=event_found,
            non_event_keywords_found=non_event_found,
            rejection_reason="non_event_topic_dominant",
        )

    return EventFilterResult(
        passed=True,
        event_score=event_score,
        event_keywords_found=event_found,
        non_event_keywords_found=non_event_found,
    )


def is_actual_disaster_event(article_text: str) -> bool:
    return get_actual_disaster_event_result(article_text).passed


def has_strong_foreign_signal(text: str) -> bool:
    """Reject articles that mention foreign disasters without any Indonesian signal."""
    normalized = normalize_for_match(text)
    return any(hint in normalized for hint in NEGATIVE_FOREIGN_HINTS)


def has_specific_indonesia_location(found_keywords: Iterable[str]) -> bool:
    generic = {"indonesia", "ri"}
    return any(keyword.casefold() not in generic for keyword in found_keywords)
