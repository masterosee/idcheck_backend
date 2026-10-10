import re
import unicodedata


def norm_id(value: str) -> str:
    """Garde seulement lettres/chiffres en majuscules (ex: 01-02-03 -> 010203)."""
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def norm_name(value: str) -> str:
    """Minuscules, sans accents ni ponctuation."""
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z\s]", " ", value.lower())
    return re.sub(r"\s+", " ", value).strip()
