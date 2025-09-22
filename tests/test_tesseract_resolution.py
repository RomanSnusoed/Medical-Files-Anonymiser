from __future__ import annotations

import pytest
import pytesseract

import utils


def test_ensure_tesseract_cmd_respects_env(monkeypatch, tmp_path):
    fake_tesseract = tmp_path / "tesseract"
    fake_tesseract.write_text("#!/bin/sh\n")

    monkeypatch.setenv("TESSERACT_CMD", str(fake_tesseract))
    monkeypatch.setattr(utils.shutil, "which", lambda *_: None)
    monkeypatch.setattr(pytesseract.pytesseract, "tesseract_cmd", "unresolved")

    resolved = utils.ensure_tesseract_cmd()

    assert resolved == str(fake_tesseract)
    assert pytesseract.pytesseract.tesseract_cmd == str(fake_tesseract)


def test_ensure_tesseract_cmd_falls_back_to_which(monkeypatch, tmp_path):
    fake_tesseract = tmp_path / "bin" / "tesseract"
    fake_tesseract.parent.mkdir()
    fake_tesseract.write_text("#!/bin/sh\n")

    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.setattr(utils.os, "name", "posix")
    monkeypatch.setattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    monkeypatch.setattr(utils.shutil, "which", lambda cmd: str(fake_tesseract) if cmd == "tesseract" else None)

    resolved = utils.ensure_tesseract_cmd()

    assert resolved == str(fake_tesseract)
    assert pytesseract.pytesseract.tesseract_cmd == str(fake_tesseract)


def test_ensure_tesseract_cmd_missing(monkeypatch):
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.setattr(utils.os, "name", "posix")
    monkeypatch.setattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    monkeypatch.setattr(utils.shutil, "which", lambda *_: None)

    with pytest.raises(FileNotFoundError) as excinfo:
        utils.ensure_tesseract_cmd()

    assert "Tesseract" in str(excinfo.value)
