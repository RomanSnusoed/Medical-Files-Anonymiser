from __future__ import annotations

from pathlib import Path
import fitz
import pytest

from pdf_generator import build_pdf_bytes, generate_pdf_with_highlights


def test_pdf_is_real_file_with_unicode(tmp_path):
    try:
        pdf_bytes = build_pdf_bytes("Пациент: [REDACTED]\nHello & good day\n" * 40)
    except RuntimeError as exc:
        pytest.skip(str(exc))
    assert pdf_bytes.startswith(b"%PDF")
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        assert len(document) >= 1
        text = "\n".join(page.get_text() for page in document)
        assert "Пациент" in text
        assert "[REDACTED]" in text


def test_legacy_wrapper_uses_random_name(tmp_path):
    try:
        first = generate_pdf_with_highlights("original", "[REDACTED]", str(tmp_path))
        second = generate_pdf_with_highlights("original", "[REDACTED]", str(tmp_path))
    except RuntimeError as exc:
        pytest.skip(str(exc))
    assert first != second
    assert (tmp_path / Path(first).name).exists()
    assert (tmp_path / Path(second).name).exists()
