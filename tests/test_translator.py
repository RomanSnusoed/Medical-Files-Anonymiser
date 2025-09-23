from collections import defaultdict
from unittest.mock import MagicMock, patch

import translator


def _fake_tokenizer(model_name):
    tokenizer = MagicMock(name=f"tokenizer-{model_name}")
    tokenizer.return_value = {"input_ids": [[0]], "attention_mask": [[1]]}
    tokenizer.decode.return_value = f"translated-{model_name}"
    return tokenizer


def _fake_model(model_name):
    model = MagicMock(name=f"model-{model_name}")
    model.generate.return_value = [[0]]
    return model


def test_models_are_loaded_once_per_language():
    translator._get_model_and_tokenizer.cache_clear()
    load_counts = defaultdict(int)

    def model_loader(model_name):
        load_counts[model_name] += 1
        return _fake_model(model_name)

    with patch("translator.MarianMTModel.from_pretrained", side_effect=model_loader) as model_patch, \
            patch("translator.MarianTokenizer.from_pretrained", side_effect=_fake_tokenizer):
        translator.translate_text_de_to_en("Hallo")
        translator.translate_text_de_to_en("Wie geht's?")
        translator.translate_text_en_to_de("Hello")
        translator.translate_text_en_to_de("Good morning")
        translator.translate_text_ru_to_en("Привет")
        translator.translate_text_ru_to_en("Здравствуйте")
        translator.translate_text_en_to_ru("Hi")
        translator.translate_text_en_to_ru("Welcome")

    try:
        assert model_patch.call_count == 4
        assert load_counts["Helsinki-NLP/opus-mt-de-en"] == 1
        assert load_counts["Helsinki-NLP/opus-mt-en-de"] == 1
        assert load_counts["Helsinki-NLP/opus-mt-ru-en"] == 1
        assert load_counts["Helsinki-NLP/opus-mt-en-ru"] == 1
    finally:
        translator._get_model_and_tokenizer.cache_clear()


def test_translate_text_preserves_blank_lines(monkeypatch):
    translated_chunks = []

    class DummyTokenizer:
        def __call__(self, text, **kwargs):
            return {"text": text}

        def decode(self, token, skip_special_tokens=True):
            return f"decoded:{token}"

    class DummyModel:
        def generate(self, **kwargs):
            translated_chunks.append(kwargs["text"])
            return [kwargs["text"].upper()]

    monkeypatch.setattr(
        translator,
        "_get_model_and_tokenizer",
        lambda name: (DummyModel(), DummyTokenizer()),
    )

    result = translator._translate_text("line1\n\nline3", "dummy-model")

    assert result.split("\n") == ["decoded:LINE1", "", "decoded:LINE3"]
    assert translated_chunks == ["line1", "line3"]


def test_split_text_into_chunks_respects_bounds():
    text = "Sentence one. Sentence two. Sentence three."

    chunks = translator.split_text_into_chunks(text, max_length=25)

    assert chunks == ["Sentence one.", "Sentence two.", "Sentence three.."]
    assert all(len(chunk) <= 25 for chunk in chunks)
