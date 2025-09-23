from functools import lru_cache
from threading import Lock
from typing import Tuple

from transformers import MarianMTModel, MarianTokenizer


_MODEL_LOAD_LOCK = Lock()


@lru_cache(maxsize=None)
def _get_model_and_tokenizer(model_name: str) -> Tuple[MarianMTModel, MarianTokenizer]:
    """Load and cache Marian model/tokenizer pairs in a thread-safe manner."""
    with _MODEL_LOAD_LOCK:
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)
    return model, tokenizer


def _translate_text(text, model_name, max_length=500):
    model, tokenizer = _get_model_and_tokenizer(model_name)

    chunks = text.split("\n")
    translated_chunks = []

    for chunk in chunks:
        if chunk.strip():
            tokenized_text = tokenizer(
                chunk,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=max_length,
            )
            translated = model.generate(**tokenized_text)
            translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
            translated_chunks.append(translated_text)
        else:
            translated_chunks.append("")

    return "\n".join(translated_chunks)


def translate_text_de_to_en(text, max_length=500):
    """
    Translates German text to English.
    """
    model_name = "Helsinki-NLP/opus-mt-de-en"
    return _translate_text(text, model_name, max_length=max_length)


def translate_text_ru_to_en(text, max_length=500):
    """
    Translates Russian text to English.
    """
    model_name = "Helsinki-NLP/opus-mt-ru-en"
    return _translate_text(text, model_name, max_length=max_length)


def translate_text_en_to_de(text, max_length=500):
    """
    Translates English text to German.
    """
    model_name = "Helsinki-NLP/opus-mt-en-de"
    return _translate_text(text, model_name, max_length=max_length)


def translate_text_en_to_ru(text, max_length=500):
    """
    Translates English text to Russian.
    """
    model_name = "Helsinki-NLP/opus-mt-en-ru"
    return _translate_text(text, model_name, max_length=max_length)


def split_text_into_chunks(text, max_length=500):
    """
    Splits text into chunks of a maximum length, trying to split by sentences.
    """
    sentences = text.split(". ")
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_length:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks
