"""Small text measures used by the checks. No outside libraries."""

from __future__ import annotations

import re

_WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    """Split text into sentences. Line breaks also end a sentence."""
    parts = _SENTENCE_END.split(text.strip())
    return [p.strip() for p in parts if _WORD.search(p)]


def split_words(text: str) -> list[str]:
    return _WORD.findall(text)


def count_syllables(word: str) -> int:
    """Estimate syllables by counting vowel groups. Good enough for scoring."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    count = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(count, 1)


def reading_grade(text: str) -> float:
    """Flesch-Kincaid grade level. Grade 9 is about age 14 to 15."""
    sentences = split_sentences(text)
    words = split_words(text)
    if not sentences or not words:
        return 0.0
    syllables = sum(count_syllables(w) for w in words)
    grade = 0.39 * (len(words) / len(sentences)) + 11.8 * (syllables / len(words)) - 15.59
    return round(max(grade, 0.0), 1)


def longest_sentence(text: str) -> tuple[int, str]:
    """Return the word count and text of the longest sentence."""
    best = (0, "")
    for sentence in split_sentences(text):
        n = len(split_words(sentence))
        if n > best[0]:
            best = (n, sentence)
    return best
