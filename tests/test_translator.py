from __future__ import annotations

import sys
import types
from contextlib import nullcontext
from unittest.mock import Mock

import pytest
import translator


class FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return list(text)

    def prepare_for_model(self, ids, **kwargs):
        return {"input_ids": ids}

    def decode(self, ids, skip_special_tokens=True):
        return "".join(ids)


class FakeModel:
    def eval(self):
        return self

    def generate(self, input_ids):
        return [input_ids]


def test_no_silent_truncation_and_preserve_newlines(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", types.SimpleNamespace(inference_mode=nullcontext))
    monkeypatch.setattr(
        translator, "_get_model_and_tokenizer", lambda name: (FakeModel(), FakeTokenizer())
    )
    original = "a" * 120 + "\n\n" + "b" * 120
    assert translator._translate_text(original, "example", max_length=20) == original


def test_redaction_placeholders_never_reach_model(monkeypatch):
    inputs = []

    def fake_translate(text, name, max_length=500):
        inputs.append(text)
        return text.upper()

    monkeypatch.setattr(translator, "_translate_text", fake_translate)
    result = translator.translate_preserving_markers(
        "hello [REDACTED] world [REDACTED]", "en", "de"
    )
    assert result == "HELLO [REDACTED] WORLD [REDACTED]"
    assert all("[REDACTED]" not in part for part in inputs)


def test_same_language_skips_translation(monkeypatch):
    monkeypatch.setattr(
        translator, "_translate_text", lambda *a, **kw: pytest.fail("unnecessary translation")
    )
    assert translator.translate_preserving_markers("Hi [REDACTED]", "en", "en") == "Hi [REDACTED]"


def test_invalid_pair_raises():
    with pytest.raises(ValueError):
        translator.translate_preserving_markers("test", "en", "es")


def test_model_loading_is_cached(monkeypatch):
    fake_transformers = types.ModuleType("transformers")
    factory = Mock(side_effect=lambda _name: FakeTokenizer())
    model_factory = Mock(side_effect=lambda _name: FakeModel())
    fake_transformers.MarianTokenizer = types.SimpleNamespace(from_pretrained=factory)
    fake_transformers.MarianMTModel = types.SimpleNamespace(from_pretrained=model_factory)
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    translator._get_model_and_tokenizer.cache_clear()
    try:
        first = translator._get_model_and_tokenizer("mock-model")
        assert first is translator._get_model_and_tokenizer("mock-model")
        assert factory.call_count == 1
        assert model_factory.call_count == 1
    finally:
        translator._get_model_and_tokenizer.cache_clear()
