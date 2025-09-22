from __future__ import annotations

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest


# Stub ``presidio_analyzer`` so importing ``cleaners`` does not attempt to download spaCy models.
_fake_analyzer_instance = MagicMock(name="AnalyzerEngineInstance")
_fake_analyzer_instance.analyze.return_value = []

_fake_presidio = types.ModuleType("presidio_analyzer")
_fake_presidio.AnalyzerEngine = MagicMock(
    name="AnalyzerEngine", return_value=_fake_analyzer_instance
)


# Stub ``transformers`` to avoid heavy dependencies and network calls.
class _FakeMarianMTModel:
    @classmethod
    def from_pretrained(cls, *args, **kwargs):  # pragma: no cover - should be patched in tests
        raise RuntimeError("from_pretrained should be patched during tests")


class _FakeMarianTokenizer:
    @classmethod
    def from_pretrained(cls, *args, **kwargs):  # pragma: no cover - should be patched in tests
        raise RuntimeError("from_pretrained should be patched during tests")


_fake_ner_pipeline = MagicMock(name="ner_pipeline")

_fake_transformers = types.ModuleType("transformers")
_fake_transformers.pipeline = MagicMock(
    name="pipeline", return_value=_fake_ner_pipeline
)
_fake_transformers.MarianMTModel = _FakeMarianMTModel
_fake_transformers.MarianTokenizer = _FakeMarianTokenizer


# Stub ``roberta`` module used by ``cleaners``.
class _FakeXlmRobertaNER:
    def __init__(self, *args, **kwargs):
        pass

    def analyze(self, text):  # pragma: no cover - not exercised in tests
        return []


_fake_roberta = types.ModuleType("roberta")
_fake_roberta.XlmRobertaNER = _FakeXlmRobertaNER


sys.modules["presidio_analyzer"] = _fake_presidio
sys.modules["transformers"] = _fake_transformers
sys.modules["roberta"] = _fake_roberta


@pytest.fixture(scope="session")
def cleaners_module():
    """Provide the imported ``cleaners`` module using the stubbed dependencies."""

    return importlib.import_module("cleaners")


@pytest.fixture()
def analyzer_mock(cleaners_module):
    cleaners_module.analyzer.analyze.reset_mock()
    cleaners_module.analyzer.analyze.return_value = []
    cleaners_module.analyzer.analyze.side_effect = None
    yield cleaners_module.analyzer
    cleaners_module.analyzer.analyze.return_value = []
    cleaners_module.analyzer.analyze.side_effect = None


@pytest.fixture()
def ner_pipeline_mock_fixture(cleaners_module):
    cleaners_module.ner_pipeline.reset_mock()
    cleaners_module.ner_pipeline.return_value = []
    cleaners_module.ner_pipeline.side_effect = None
    yield cleaners_module.ner_pipeline
    cleaners_module.ner_pipeline.return_value = []
    cleaners_module.ner_pipeline.side_effect = None


@pytest.fixture(scope="session")
def transformers_pipeline_mock():
    return _fake_ner_pipeline
