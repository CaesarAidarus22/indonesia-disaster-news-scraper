from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd


DATA_COLUMNS = [
    "id",
    "title",
    "url",
    "source",
    "published_date",
    "author",
    "content",
    "disaster_keywords_found",
    "indonesia_location_keywords_found",
    "event_score",
    "rejection_reason",
    "scraped_at",
]


def remove_duplicate_urls(records: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    unique_records: list[dict] = []

    for record in records:
        url = (record.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        unique_records.append(record)

    return unique_records


def save_to_csv(records: list[dict], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records, columns=DATA_COLUMNS)
    df.to_csv(output, index=False, encoding="utf-8")


def save_to_json(records: list[dict], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)
