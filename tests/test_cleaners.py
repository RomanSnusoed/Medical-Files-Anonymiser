from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


def test_load_ignore_words_returns_set(cleaners_module):
    ignorewords = cleaners_module.load_ignore_words(Path("ignorewords.txt"))
    assert isinstance(ignorewords, set)
    assert "Alanine" in ignorewords
    assert "Alison" not in ignorewords


def test_is_valid_date_format_accepts_various_patterns(cleaners_module):
    assert cleaners_module.is_valid_date_format("Date of Birth: 01/02/2003")
    assert cleaners_module.is_valid_date_format("1 January 2020")
    assert cleaners_module.is_valid_date_format("Patient ID: AB-1234") is False


def test_clean_and_remove_personal_info_redacts_all_sources(
    cleaners_module, analyzer_mock, ner_pipeline_mock_fixture, monkeypatch
):
    text = "My name is Quasar and I live in New York. Call me at 555-1234."

    FakeResult = type("FakeResult", (), {})
    fake_person = FakeResult()
    fake_person.start = text.index("Quasar")
    fake_person.end = fake_person.start + len("Quasar")
    fake_person.entity_type = "PERSON"

    analyzer_mock.analyze.return_value = [fake_person]
    ner_pipeline_mock_fixture.return_value = [
        {
            "start": text.index("New York"),
            "end": text.index("New York") + len("New York"),
            "entity_group": "LOCATION",
        }
    ]

    monkeypatch.setattr(cleaners_module, "detect", lambda *_: "en")

    cleaned, logs = cleaners_module.clean_and_remove_personal_info(text)

    assert "Quasar" not in cleaned
    assert "New York" not in cleaned
    assert "[REDACTED]" in cleaned
    assert any("Removing" in entry for entry in logs)


def test_clean_and_remove_personal_info_handles_presidio_error(
    cleaners_module, analyzer_mock, monkeypatch
):
    analyzer_mock.analyze.side_effect = RuntimeError("boom")
    monkeypatch.setattr(cleaners_module, "detect", lambda *_: "en")

    cleaned, logs = cleaners_module.clean_and_remove_personal_info("Nothing personal")

    assert cleaned == "Nothing personal"
    assert any("Presidio error" in entry for entry in logs)


def test_clean_and_remove_personal_info_regex_redacts(
    cleaners_module, ner_pipeline_mock_fixture, monkeypatch
):
    monkeypatch.setattr(cleaners_module, "detect", lambda *_: "en")
    ner_pipeline_mock_fixture.return_value = []

    text = "Contact: roman@example.com"
    cleaned, logs = cleaners_module.clean_and_remove_personal_info(text)

    assert "roman@example.com" not in cleaned
    assert cleaned.count("[REDACTED]") == 1
    assert any("email" in entry for entry in logs)


def test_process_text_in_chunks_preserves_order(cleaners_module, monkeypatch):
    calls = []

    def fake_clean(text):
        calls.append(text)
        return text.upper(), [f"processed {text}"]

    monkeypatch.setattr(cleaners_module, "clean_and_remove_personal_info", fake_clean)

    cleaned, logs = cleaners_module.process_text_in_chunks("aa bb", chunk_size=2)

    assert cleaned == "AA BB"
    assert calls == ["aa", " b", "b"]
    assert len(logs) == len(calls)


def test_load_ignore_words_missing_file(cleaners_module, tmp_path, monkeypatch):
    missing_file = tmp_path / "missing.txt"
    mock_print = MagicMock()
    monkeypatch.setattr("builtins.print", mock_print)

    ignorewords = cleaners_module.load_ignore_words(missing_file)

    assert ignorewords == set()
    mock_print.assert_called_once()
