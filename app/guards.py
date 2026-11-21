import re

LEET_MAP = {
    "9": "ق",
    "7": "ح",
    "3": "ع",
    "2": "ء",
    "5": "خ",
    "6": "ط",
    "8": "غ",
}


def has_text(comment_text: str | None) -> bool:
    return bool(comment_text and comment_text.strip())


def normalize_for_analysis(text: str) -> tuple[str, bool]:
    obfuscated = False
    cleaned = text.strip()

    if re.search(r"(?<=\w)[\.\*\_\-\~]+(?=\w)", cleaned):
        obfuscated = True
        cleaned = re.sub(r"(?<=\w)[\.\*\_\-\~]+(?=\w)", "", cleaned)

    if re.search(r"(.)\1{2,}", cleaned):
        obfuscated = True
        cleaned = re.sub(r"(.)\1{2,}", r"\1\1", cleaned)

    lower_cleaned = cleaned.lower()
    if re.search(r"[a-z]+[0-9]+|[0-9]+[a-z]+", lower_cleaned):
        obfuscated = True
        converted_chars = [LEET_MAP.get(ch, ch) for ch in lower_cleaned]
        cleaned = "".join(converted_chars)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, obfuscated
