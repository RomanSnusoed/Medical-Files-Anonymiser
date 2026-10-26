from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import cleaners


@pytest.mark.parametrize("spans,expected", [
    ([(0, 5, "[REDACTED]"), (0, 5, "[REDACTED]")], "[REDACTED] Smith"),
    ([(0, 11, "[REDACTED]"), (0, 5, "[REDACTED]")], "[REDACTED]"),
    ([(0, 5, "[REDACTED]"), (3, 11, "[REDACTED]")], "[REDACTED]"),
])
def test_merge_overlaps(spans, expected):
    assert cleaners.apply_replacements("Alice Smith", spans) == expected


def test_unrelated_spans_preserve_text():
    assert cleaners.apply_replacements(
        "Alice met Bob", [(0, 5, "[REDACTED]"), (10, 13, "[REDACTED]")]
    ) == "[REDACTED] met [REDACTED]"


def test_empty_and_invalid_spans():
    assert cleaners.apply_replacements("abc", [(4, 5, "[REDACTED]"), (-1, 2, "[REDACTED]")]) == "abc"
    assert cleaners.process_text_in_chunks("") == ("", [])


def test_detectors_and_regex(monkeypatch):
    text = "Alice visited Berlin. Email alice@example.com"
    a = MagicMock()
    a.analyze.return_value = [SimpleNamespace(start=0, end=5, entity_type="PERSON")]
    n = MagicMock(return_value=[{"start": 14, "end": 20, "entity_group": "LOC"}])
    monkeypatch.setattr(cleaners, "_get_analyzer", lambda: a)
    monkeypatch.setattr(cleaners, "_get_ner_pipeline", lambda: n)
    result, logs = cleaners.process_text_in_chunks(text, include_pii=False)
    assert "Alice" not in result
    assert "Berlin" not in result
    assert "alice@example.com" not in result
    assert all("alice@example.com" not in line for line in logs)
    assert result.count("[REDACTED]") == 3


def test_model_failure_aborts(monkeypatch):
    a = MagicMock()
    a.analyze.side_effect = RuntimeError("model unavailable")
    monkeypatch.setattr(cleaners, "_get_analyzer", lambda: a)
    monkeypatch.setattr(cleaners, "_get_ner_pipeline", lambda: lambda s: [])
    with pytest.raises(cleaners.AnonymizationError):
        cleaners.process_text_in_chunks("Alice visited Berlin.")


def test_ignore_words_missing_file(tmp_path):
    assert cleaners.load_ignore_words(tmp_path / "missing.txt") == set()


def test_chunk_overlaps_are_valid():
    windows = list(cleaners._windows("a" * 300, 120, 20))
    assert windows[0][0] == 0
    assert windows[-1][1] == 300
    assert all(start < end for start, end, _ in windows)


def test_dates_and_ages():
    assert cleaners.is_valid_date_format("2003-02-01")
    assert cleaners.is_valid_date_format("29 years old")
    assert not cleaners.is_valid_date_format("patient is stable")
