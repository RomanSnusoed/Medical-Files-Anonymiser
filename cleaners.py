"""PII detection and safe redaction of overlapping entity spans.

Treat this as a best-effort detection system, not a guarantee of anonymisation.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable

REDACTION = "[REDACTED]"
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_OVERLAP = 180


class AnonymizationError(RuntimeError):
    """A required detection stage could not complete reliably."""


def load_ignore_words(file_path: str | Path | None = None) -> set[str]:
    path = Path(file_path) if file_path else Path(__file__).with_name("ignorewords.txt")
    try:
        with path.open(encoding="utf-8") as stream:
            return {line.strip().casefold() for line in stream if line.strip()}
    except FileNotFoundError:
        return set()


ignorewords = load_ignore_words()


@lru_cache(maxsize=1)
def _get_analyzer():
    from presidio_analyzer import AnalyzerEngine
    return AnalyzerEngine()


@lru_cache(maxsize=1)
def _get_ner_pipeline():
    from transformers import pipeline
    return pipeline(
        "token-classification",
        model="Davlan/xlm-roberta-base-ner-hrl",
        aggregation_strategy="simple",
    )


def merge_replacements(
    replacements: Iterable[tuple[int, int, str]], text_length: int
) -> list[tuple[int, int, str]]:
    """Return valid, non-overlapping spans in source-text coordinates."""
    spans = sorted(
        (start, end)
        for start, end, _ in replacements
        if isinstance(start, int)
        and isinstance(end, int)
        and 0 <= start < end <= text_length
    )
    if not spans:
        return []

    merged = [[spans[0][0], spans[0][1]]]
    for start, end in spans[1:]:
        if start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end, REDACTION) for start, end in merged]


def apply_replacements(text: str, replacements: Iterable[tuple[int, int, str]]) -> str:
    """Apply replacement spans once, merging overlapping detector outputs."""
    merged = merge_replacements(replacements, len(text))
    result: list[str] = []
    cursor = 0
    for start, end, marker in merged:
        result.extend((text[cursor:start], marker))
        cursor = end
    result.append(text[cursor:])
    return "".join(result)


def is_valid_date_format(text: str) -> bool:
    patterns = (
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*,?\s*\d{4}\b",
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{1,3}[ -]?(?:year|years|yr|yrs)(?:[ -]?old)?\b",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


PATTERNS = {
    "EMAIL_ADDRESS": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "PATIENT_ID": re.compile(r"\bPatient ID:\s*[A-Z]{2}-\d{4}\b", re.IGNORECASE),
    "PATIENT_FILE": re.compile(r"\bPatient File:\s*[A-Z]{2}-[A-Z]{3}-\d{5}\b", re.IGNORECASE),
    "PHONE_NUMBER": re.compile(r"(?<!\w)(?:\+\d{1,3}[ -]?)?(?:\(\d{2,4}\)|\d{2,4})[ -.]*\d{3,4}[ -.]*\d{3,5}(?!\w)"),
}

# This model labels entities PER/LOC/ORG/MISC (not PERSON/LOCATION).
NER_LABELS = {"PER", "LOC", "ORG"}


def _windows(text: str, chunk_size: int, overlap: int):
    if chunk_size <= 0 or not 0 <= overlap < chunk_size // 2:
        raise ValueError("chunk_size must be positive and overlap smaller than half")
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Preserve a little surrounding context without losing global offsets.
        if end < len(text):
            split = max(text.rfind(" ", start + chunk_size // 2, end), text.rfind("\n", start + chunk_size // 2, end))
            if split > start:
                end = split + 1
        yield start, end, text[start:end]
        if end == len(text):
            break
        start = end - overlap


def _should_redact(value: str) -> bool:
    # Never trust an ignore-word list to override an explicit PII detection.
    # Common person names and cities may appear in broad dictionaries.
    return bool(value.strip())


def _log(source: str, label: str, start: int, end: int, value: str, include_pii: bool) -> str:
    message = f"{source}: detected {label} at [{start}:{end}]"
    return f"{message} = {value!r}" if include_pii else message


def process_text_in_chunks(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    *,
    include_pii: bool = False,
    language: str = "en",
) -> tuple[str, list[str]]:
    """Redact text with overlapping windows, retaining original absolute offsets.

    Both NLP detectors are mandatory. On model failure, abort rather than
    returning incompletely cleaned medical content.
    """
    if not text:
        return "", []
    if language not in {"en", "de", "ru"}:
        raise ValueError("Unsupported detection language")
    if overlap >= chunk_size // 2:
        overlap = max(0, chunk_size // 4)
    if chunk_size < 2:
        raise ValueError("chunk_size must be at least 2")

    try:
        analyzer = _get_analyzer() if language == "en" else None
        ner = _get_ner_pipeline()
    except Exception as exc:
        raise AnonymizationError("Could not initialize PII detection models") from exc

    replacements: list[tuple[int, int, str]] = []
    logs: list[str] = []
    try:
        for offset, _end, window in _windows(text, chunk_size, overlap):
            presidio_results = (
                analyzer.analyze(
                    text=window,
                    language="en",
                    entities=["PERSON", "LOCATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "DATE_TIME"],
                )
                if analyzer is not None else []
            )
            for entity in presidio_results:
                start, end = int(entity.start), int(entity.end)
                if not 0 <= start < end <= len(window):
                    continue
                value = window[start:end]
                label = entity.entity_type
                if label == "DATE_TIME" and not is_valid_date_format(value):
                    continue
                if _should_redact(value):
                    replacements.append((offset + start, offset + end, REDACTION))
                    logs.append(_log("Presidio", label, offset + start, offset + end, value, include_pii))

            for entity in ner(window):
                label = str(entity.get("entity_group", "")).upper()
                if label not in NER_LABELS:
                    continue
                start, end = int(entity["start"]), int(entity["end"])
                if not 0 <= start < end <= len(window):
                    continue
                value = window[start:end]
                if _should_redact(value):
                    replacements.append((offset + start, offset + end, REDACTION))
                    logs.append(_log("XLM-R", label, offset + start, offset + end, value, include_pii))

        # Regexes scan the complete original text; boundaries never split IDs.
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                if _should_redact(match.group()):
                    replacements.append((match.start(), match.end(), REDACTION))
                    logs.append(
                        _log("Regex", label, match.start(), match.end(), match.group(), include_pii)
                    )
    except Exception as exc:
        raise AnonymizationError("PII detection failed; no document was released") from exc

    merged = merge_replacements(replacements, len(text))
    logs.append(f"Completed redaction: {len(merged)} unique spans")
    return apply_replacements(text, merged), logs


def clean_and_remove_personal_info(text: str, *, include_pii: bool = False, language: str = "en"):
    """Compatibility entry point for existing callers."""
    return process_text_in_chunks(text, include_pii=include_pii, language=language)
