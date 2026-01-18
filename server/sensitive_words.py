import os
from pathlib import Path
from typing import Iterable, List


DEFAULT_WORDS = [
    "垃圾",
    "广告",
    "色情",
    "赌博",
    "诈骗",
]


def _load_words_from_file(path: Path) -> List[str]:
    try:
        data = path.read_text(encoding="utf-8")
    except Exception:
        return []
    words = []
    for raw in data.splitlines():
        word = raw.strip()
        if not word or word.startswith("#"):
            continue
        words.append(word)
    return words


def load_sensitive_words() -> List[str]:
    env_path = os.getenv("SENSITIVE_WORDS_FILE")
    if env_path:
        path = Path(env_path)
        if path.exists():
            words = _load_words_from_file(path)
            if words:
                return words
    return DEFAULT_WORDS


def filter_sensitive(text: str, words: Iterable[str]) -> str:
    filtered = text
    for word in words:
        if not word:
            continue
        filtered = filtered.replace(word, "***")
    return filtered
