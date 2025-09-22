from __future__ import annotations

from pathlib import Path
import pdf_generator


def test_generate_pdf_with_highlights_creates_incremented_file(tmp_path, monkeypatch):
    output_dir = tmp_path / "pdf_outputs"
    output_dir.mkdir()
    (output_dir / "output_1.pdf").write_text("dummy")
    (output_dir / "output_2.pdf").write_text("dummy")

    instances = []
    draw_calls = []

    class DummyCanvas:
        def __init__(self, path, pagesize):
            self.path = path
            self.pagesize = pagesize
            self.saved = False
            self.fill_color = None
            instances.append(self)

        def setFont(self, *args, **kwargs):
            pass

        def setFillColor(self, color):
            self.fill_color = color

        def drawString(self, x, y, text):
            draw_calls.append((self.fill_color, text))

        def stringWidth(self, text, font, size):
            return len(text)

        def showPage(self):
            pass

        def save(self):
            self.saved = True

    monkeypatch.setattr(pdf_generator.canvas, "Canvas", DummyCanvas)
    monkeypatch.setattr(pdf_generator.colors, "black", "BLACK")
    monkeypatch.setattr(pdf_generator.colors, "red", "RED")
    output_path = pdf_generator.generate_pdf_with_highlights(
        "Original [REDACTED] text",
        "Clean [REDACTED] line\nSecond line without secret",
        output_folder=str(output_dir),
    )

    assert instances, "Canvas should have been instantiated"
    canvas_instance = instances[0]
    assert Path(canvas_instance.path).name == "output_3.pdf"
    assert canvas_instance.saved is True
    assert ("RED", "[REDACTED]") in draw_calls
    assert all(color in {"BLACK", "RED"} for color, _ in draw_calls)
    assert Path(output_path).name == "output_3.pdf"
