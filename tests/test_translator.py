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
