"""Unit tests deliberately patch large NLP models; integration tests run separately."""
from __future__ import annotations

import pytest


@pytest.fixture()
def fake_detectors(monkeypatch):
    import cleaners

    class Analyzer:
        def analyze(self, text, language, entities):
            return []

    monkeypatch.setattr(cleaners, "_get_analyzer", lambda: Analyzer())
    monkeypatch.setattr(cleaners, "_get_ner_pipeline", lambda: lambda text: [])
