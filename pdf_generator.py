"""Reconstruct a text-only PDF containing colored redaction markers.

This does not modify or redact the original PDF's image/text layers.
"""
from __future__ import annotations

import io
import os
import secrets
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

MARKER = "[REDACTED]"


def _unicode_font() -> str:
    candidates = [
        os.getenv("PDF_FONT_PATH", ""),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\DejaVuSans.ttf",
    ]
    for location in candidates:
        if location and Path(location).is_file():
            if "MedFileUnicode" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("MedFileUnicode", location))
            return "MedFileUnicode"
    raise RuntimeError(
        "No Unicode TrueType font available. Install DejaVu Sans "
        "or provide PDF_FONT_PATH to an installed .ttf font."
    )


def build_pdf_bytes(cleaned_text: str) -> bytes:
    """Return document bytes without writing sensitive content to the filesystem."""
    output = io.BytesIO()
    font = _unicode_font()
    style = ParagraphStyle(
        "MedicalText",
        fontName=font,
        fontSize=9,
        leading=14,
        textColor=colors.black,
        wordWrap="CJK",
        splitLongWords=True,
        spaceAfter=2,
    )
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=45,
        rightMargin=45,
        topMargin=45,
        bottomMargin=45,
        title="Redacted document (text-only reconstruction)",
        author="MedFile Anonymiser",
    )
    story = []
    for line in cleaned_text.split("\n"):
        if not line.strip():
            story.append(Spacer(1, 8))
            continue
        parts = line.split(MARKER)
        rich = (f'<font color="#C62828">{MARKER}</font>').join(
            escape(part) for part in parts
        )
        story.append(Paragraph(rich or " ", style))
    if not story:
        story = [Paragraph("(empty document)", style)]
    doc.build(story)
    return output.getvalue()


def generate_pdf_with_highlights(
    original_text: str, cleaned_text: str, output_folder: str = "pdf_outputs"
) -> str:
    """Compatibility wrapper for the original CLI; web uses build_pdf_bytes."""
    del original_text
    directory = Path(output_folder)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"redacted_{secrets.token_hex(12)}.pdf"
    path.write_bytes(build_pdf_bytes(cleaned_text))
    return str(path)
