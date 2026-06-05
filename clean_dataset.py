from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from utils.filters import (
    DISASTER_KEYWORDS,
    NEGATIVE_FOREIGN_HINTS,
    find_keywords,
    get_actual_disaster_event_result,
    has_specific_indonesia_location,
    has_strong_foreign_signal,
    is_disaster_article,
    is_indonesia_related_article,
)
from utils.text import clean_text, normalize_for_match


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
CLEANED_PATH = PROCESSED_DIR / "cleaned_disaster_news.csv"
REJECTED_PATH = PROCESSED_DIR / "rejected_disaster_news.csv"
REPORT_PATH = PROCESSED_DIR / "cleaning_report.txt"


REJECTED_CHANNEL_KEYWORDS = [
    "properti",
    "property",
    "otomotif",
    "automotive",
    "homey",
    "cekfakta",
    "cek-fakta",
    "politik",
    "opini",
    "hiburan",
    "entertainment",
    "olahraga",
    "sport",
    "bola",
]


ACCEPT_EVENT_KEYWORDS = [
    "terjadi",
    "melanda",
    "mengguncang",
    "merendam",
    "terendam",
    "terdampak",
    "korban",
    "korban jiwa",
    "tewas",
    "meninggal",
    "pengungsi",
    "mengungsi",
    "evakuasi",
    "kerusakan",
    "rusak",
    "jebol",
    "hanyut",
    "bantuan logistik",
    "pascabencana",
    "pasca bencana",
]


STRONG_ACCEPT_KEYWORDS = [
    "korban",
    "korban jiwa",
    "tewas",
    "meninggal",
    "pengungsi",
    "mengungsi",
    "evakuasi",
    "kerusakan",
    "rusak",
    "bantuan logistik",
    "pascabencana",
    "pasca bencana",
]


NON_EVENT_TOPIC_KEYWORDS = [
    "harga properti",
    "properti",
    "kendaraan",
    "otomotif",
    "tips",
    "penelitian",
    "riset",
    "studi",
    "sejarah",
    "purba",
    "politik",
    "opini",
    "mitigasi",
    "pencegahan",
    "sosialisasi",
    "pembangunan",
    "revitalisasi",
    "normalisasi",
    "proyek",
]


DISASTER_TYPE_KEYWORDS = {
    "banjir": ["banjir", "banjir bandang", "terendam", "merendam"],
    "gempa bumi": ["gempa bumi", "gempa", "mengguncang"],
    "tsunami": ["tsunami"],
    "tanah longsor": ["tanah longsor", "longsor"],
    "kebakaran": ["kebakaran", "terbakar"],
    "erupsi gunung api": ["erupsi", "gunung meletus", "awan panas", "lahar"],
    "angin puting beliung": ["puting beliung", "angin kencang", "angin ribut"],
    "kekeringan": ["kekeringan", "krisis air"],
    "abrasi": ["abrasi"],
    "gelombang tinggi": ["gelombang tinggi"],
    "kecelakaan industri": ["kecelakaan industri", "ledakan pabrik", "pabrik meledak"],
}


CLEAN_COLUMNS = [
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
    "clean_status",
    "clean_reason",
    "disaster_type",
    "is_indonesia_event",
]


def load_raw_csvs() -> pd.DataFrame:
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    frames: list[pd.DataFrame] = []
    for file_path in files:
        frame = pd.read_csv(file_path)
        frame["raw_file"] = file_path.name
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    for column in CLEAN_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    text_columns = ["title", "url", "source", "published_date", "author", "content"]
    for column in text_columns:
        df[column] = df[column].fillna("").astype(str).map(clean_text)

    df["event_score"] = pd.to_numeric(df["event_score"], errors="coerce").fillna(0).astype(int)
    return df


def deduplicate_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    duplicate_mask = df.duplicated(subset=["url"], keep="first") | df.duplicated(subset=["title"], keep="first")
    duplicates = df[duplicate_mask].copy()
    duplicates["clean_status"] = "rejected"
    duplicates["clean_reason"] = "duplicate_url_or_title"
    duplicates["is_indonesia_event"] = False

    unique_df = df[~duplicate_mask].copy()
    return unique_df, duplicates


def is_rejected_channel(url: str) -> bool:
    parsed = urlparse(url)
    path = normalize_for_match(parsed.path.replace("-", " ").replace("_", " "))
    host = normalize_for_match(parsed.netloc)
    combined = f"{host} {path}"
    return any(keyword in combined for keyword in REJECTED_CHANNEL_KEYWORDS)


def infer_disaster_type(text: str) -> str:
    scores: dict[str, int] = {}
    for disaster_type, keywords in DISASTER_TYPE_KEYWORDS.items():
        found = find_keywords(text, keywords)
        if found:
            scores[disaster_type] = len(found)

    if not scores:
        found_disaster = find_keywords(text, DISASTER_KEYWORDS)
        return found_disaster[0] if found_disaster else ""

    return max(scores, key=scores.get)


def classify_row(row: pd.Series) -> dict:
    text = f"{row.get('title', '')} {row.get('content', '')}"
    url = str(row.get("url", ""))

    disaster = is_disaster_article(text)
    indonesia = is_indonesia_related_article(text)
    event = get_actual_disaster_event_result(text)
    accept_event_found = find_keywords(text, ACCEPT_EVENT_KEYWORDS)
    strong_accept_found = find_keywords(text, STRONG_ACCEPT_KEYWORDS)
    non_event_found = find_keywords(text, NON_EVENT_TOPIC_KEYWORDS)
    disaster_type = infer_disaster_type(text)

    is_indonesia_event = bool(indonesia.passed and has_specific_indonesia_location(indonesia.found_keywords))
    if has_strong_foreign_signal(text) and not is_indonesia_event:
        return rejected(row, "foreign_disaster", disaster_type, is_indonesia_event)

    if any(hint in normalize_for_match(text) for hint in NEGATIVE_FOREIGN_HINTS) and not is_indonesia_event:
        return rejected(row, "foreign_location_signal", disaster_type, is_indonesia_event)

    if is_rejected_channel(url):
        return rejected(row, "rejected_channel", disaster_type, is_indonesia_event)

    if not disaster.passed:
        return rejected(row, "no_disaster_keyword", disaster_type, is_indonesia_event)

    if not indonesia.passed:
        return rejected(row, "no_indonesia_location_keyword", disaster_type, is_indonesia_event)

    if not accept_event_found and not event.passed:
        return rejected(row, "no_actual_event_or_impact", disaster_type, is_indonesia_event)

    if len(non_event_found) >= max(len(accept_event_found), event.event_score, 1) and not strong_accept_found:
        return rejected(row, "non_event_topic_dominant", disaster_type, is_indonesia_event)

    if not disaster_type:
        return rejected(row, "unknown_disaster_type", disaster_type, is_indonesia_event)

    return accepted(row, "accepted_actual_indonesia_disaster_event", disaster_type, True)


def accepted(row: pd.Series, reason: str, disaster_type: str, is_indonesia_event: bool) -> dict:
    output = row_to_record(row)
    output.update(
        {
            "clean_status": "accepted",
            "clean_reason": reason,
            "disaster_type": disaster_type,
            "is_indonesia_event": bool(is_indonesia_event),
        }
    )
    return output


def rejected(row: pd.Series, reason: str, disaster_type: str, is_indonesia_event: bool) -> dict:
    output = row_to_record(row)
    output.update(
        {
            "clean_status": "rejected",
            "clean_reason": reason,
            "disaster_type": disaster_type,
            "is_indonesia_event": bool(is_indonesia_event),
        }
    )
    return output


def row_to_record(row: pd.Series) -> dict:
    return {column: row.get(column, "") for column in CLEAN_COLUMNS}


def write_report(accepted_df: pd.DataFrame, rejected_df: pd.DataFrame, total_raw: int, total_unique: int) -> None:
    lines: list[str] = []
    lines.append("Cleaning Report")
    lines.append("================")
    lines.append(f"Raw rows: {total_raw}")
    lines.append(f"Unique rows after URL/title deduplication: {total_unique}")
    lines.append(f"Accepted rows: {len(accepted_df)}")
    lines.append(f"Rejected rows: {len(rejected_df)}")
    lines.append("")

    lines.append("Accepted per source")
    lines.append("-------------------")
    append_source_counts(lines, accepted_df)
    lines.append("")

    lines.append("Rejected per source")
    lines.append("-------------------")
    append_source_counts(lines, rejected_df)
    lines.append("")

    lines.append("Rejected reasons")
    lines.append("----------------")
    for reason, count in Counter(rejected_df.get("clean_reason", [])).most_common():
        lines.append(f"{reason}: {count}")
    lines.append("")

    lines.append("Accepted disaster types")
    lines.append("-----------------------")
    for disaster_type, count in Counter(accepted_df.get("disaster_type", [])).most_common():
        lines.append(f"{disaster_type}: {count}")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_source_counts(lines: list[str], df: pd.DataFrame) -> None:
    if df.empty or "source" not in df.columns:
        lines.append("(none)")
        return

    by_source = defaultdict(int)
    for source in df["source"].fillna("").astype(str):
        by_source[source or "(unknown)"] += 1

    for source, count in sorted(by_source.items()):
        lines.append(f"{source}: {count}")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = prepare_dataframe(load_raw_csvs())
    unique_df, duplicate_rejections = deduplicate_rows(raw_df)

    accepted_records: list[dict] = []
    rejected_records: list[dict] = duplicate_rejections[CLEAN_COLUMNS].to_dict("records")

    for _, row in unique_df.iterrows():
        record = classify_row(row)
        if record["clean_status"] == "accepted":
            accepted_records.append(record)
        else:
            rejected_records.append(record)

    accepted_df = pd.DataFrame(accepted_records, columns=CLEAN_COLUMNS)
    rejected_df = pd.DataFrame(rejected_records, columns=CLEAN_COLUMNS)

    accepted_df.to_csv(CLEANED_PATH, index=False, encoding="utf-8")
    rejected_df.to_csv(REJECTED_PATH, index=False, encoding="utf-8")
    write_report(accepted_df, rejected_df, total_raw=len(raw_df), total_unique=len(unique_df))

    print(f"Accepted: {len(accepted_df)}")
    print(f"Rejected: {len(rejected_df)}")
    print(f"Saved: {CLEANED_PATH}")
    print(f"Saved: {REJECTED_PATH}")
    print(f"Saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
