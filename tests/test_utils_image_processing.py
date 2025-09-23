from __future__ import annotations

from unittest.mock import MagicMock

from PIL import Image

import utils


def test_preprocess_image_resizes_and_grayscales(tmp_path):
    image_path = tmp_path / "input.png"
    Image.new("RGB", (10, 5), color="white").save(image_path)

    processed = utils.preprocess_image(image_path)

    assert processed.size == (20, 10)
    assert processed.mode == "L"


def test_correct_image_orientation_rotates_when_needed(monkeypatch):
    original = MagicMock(name="image")
    rotated = MagicMock(name="rotated")
    original.rotate.return_value = rotated

    monkeypatch.setattr(utils, "ensure_tesseract_cmd", lambda: "tesseract")
    monkeypatch.setattr(utils.pytesseract, "image_to_osd", lambda _: "Rotate: 90\n")

    result = utils.correct_image_orientation(original)

    assert result is rotated
    original.rotate.assert_called_once_with(-90, expand=True)


def test_correct_image_orientation_returns_original_when_aligned(monkeypatch):
    original = MagicMock(name="image")

    monkeypatch.setattr(utils, "ensure_tesseract_cmd", lambda: "tesseract")
    monkeypatch.setattr(utils.pytesseract, "image_to_osd", lambda _: "Rotate: 0\n")

    result = utils.correct_image_orientation(original)

    assert result is original
    original.rotate.assert_not_called()
