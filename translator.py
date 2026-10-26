"""Lazy, cached MarianMT translation with token-aware batching."""
from __future__ import annotations

import re
from functools import lru_cache
from threading import Lock

_LOCK = Lock()
MODELS = {
    ("de", "en"): "Helsinki-NLP/opus-mt-de-en",
    ("ru", "en"): "Helsinki-NLP/opus-mt-ru-en",
    ("en", "de"): "Helsinki-NLP/opus-mt-en-de",
    ("en", "ru"): "Helsinki-NLP/opus-mt-en-ru",
}


@lru_cache(maxsize=4)
def _get_model_and_tokenizer(model_name):
    from transformers import MarianMTModel, MarianTokenizer
    with _LOCK:
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)
    model.eval()
    return model, tokenizer


def _translate_text(text, model_name, max_length=500):
    if max_length < 16:
        raise ValueError("max_length must be at least 16")
    import torch
    model, tokenizer = _get_model_and_tokenizer(model_name)
    lines = []
    for line in text.split("\n"):
        if not line.strip():
            lines.append("")
            continue
        token_ids = tokenizer.encode(line, add_special_tokens=False)
        if not token_ids:
            lines.append("")
            continue
        translated = []
        # Reserve special-token space and never silently truncate a long line.
        for pos in range(0, len(token_ids), max_length - 8):
            segment_ids = token_ids[pos:pos + max_length - 8]
            segment = tokenizer.prepare_for_model(
                segment_ids, return_tensors="pt", truncation=False
            )
            with torch.inference_mode():
                generated = model.generate(**segment)
            translated.append(tokenizer.decode(generated[0], skip_special_tokens=True))
        lines.append(" ".join(translated))
    return "\n".join(lines)


def translate_text_de_to_en(text, max_length=500):
    return _translate_text(text, MODELS["de", "en"], max_length)


def translate_text_ru_to_en(text, max_length=500):
    return _translate_text(text, MODELS["ru", "en"], max_length)


def translate_text_en_to_de(text, max_length=500):
    return _translate_text(text, MODELS["en", "de"], max_length)


def translate_text_en_to_ru(text, max_length=500):
    return _translate_text(text, MODELS["en", "ru"], max_length)


MARKER = "[REDACTED]"


def translate_preserving_markers(text: str, source: str, target: str) -> str:
    """Translate text while keeping redaction placeholders out of the model.

    The lexical content still requires human verification before sharing.
    """
    if not text or source == target:
        return text
    if source != "en" and target != "en":
        return translate_preserving_markers(
            translate_preserving_markers(text, source, "en"), "en", target
        )
    model_name = MODELS.get((source, target))
    if model_name is None:
        raise ValueError(f"Unsupported translation pair: {source} -> {target}")
    pieces = re.split(r"(\\[REDACTED\\])", text)
    return "".join(
        piece if piece == MARKER or not piece.strip() else _translate_text(piece, model_name)
        for piece in pieces
    )
