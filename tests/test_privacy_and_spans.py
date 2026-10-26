from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import cleaners


def test_overlapping_detection_sources_are_coalesced(monkeypatch):
    text = "Alice Smith visited Berlin."
    analyzer = MagicMock()
    analyzer.analyze.return_value = [
        SimpleNamespace(start=0, end=11, entity_type="PERSON")
    ]
    model = MagicMock(return_value=[
        {"start": 0, "end": 5, "entity_group": "PER"},
        {"start": 20, "end": 26, "entity_group": "LOC"},
    ])
    monkeypatch.setattr(cleaners, "_get_analyzer", lambda: analyzer)
    monkeypatch.setattr(cleaners, "_get_ner_pipeline", lambda: model)
    cleaned, logs = cleaners.process_text_in_chunks(text)
    assert cleaned.startswith("[REDACTED] visited")
    assert "Smith" not in cleaned
    assert all("Alice" not in log for log in logs)


def test_verbose_logging_is_explicit_opt_in(monkeypatch):
    analyzer = MagicMock()
    analyzer.analyze.return_value = [SimpleNamespace(start=0, end=5, entity_type="PERSON")]
    monkeypatch.setattr(cleaners, "_get_analyzer", lambda: analyzer)
    monkeypatch.setattr(cleaners, "_get_ner_pipeline", lambda: lambda text: [])
    _, logs = cleaners.process_text_in_chunks("Alice visited town.", include_pii=True)
    assert any("Alice" in log for log in logs)


def test_other_language_does_not_call_english_only_presidio(monkeypatch):
    def unexpected():
        raise AssertionError("English Presidio should not be used for German")

    monkeypatch.setattr(cleaners, "_get_analyzer", unexpected)
    monkeypatch.setattr(cleaners, "_get_ner_pipeline", lambda: lambda text: [])
    cleaned, _ = cleaners.process_text_in_chunks(
        "Patient ID: AB-1234", language="de"
    )
    assert "AB-1234" not in cleaned
