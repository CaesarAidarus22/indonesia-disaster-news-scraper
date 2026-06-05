import re
import unicodedata


def clean_text(text: str) -> str:
    """Normalize article text without changing the Indonesian wording."""
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def normalize_for_match(text: str) -> str:
    return clean_text(text).casefold()
