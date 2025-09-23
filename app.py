from __future__ import annotations

import os
from typing import Callable, List, Optional, Tuple

from flask import Flask, flash, redirect, render_template, request, url_for
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from werkzeug.utils import secure_filename

from cleaners import process_text_in_chunks
from extractors import (
    extract_text_from_docx,
    extract_text_from_image,
    extract_text_from_pdf,
)
from openai_utils import generate_explanation
from pdf_generator import generate_pdf_with_highlights
from translator import (
    translate_text_de_to_en,
    translate_text_en_to_de,
    translate_text_en_to_ru,
    translate_text_ru_to_en,
)


ALLOWED_EXTENSIONS = {"pdf", "docx", "jpg", "jpeg", "png", "tif", "tiff"}

LANGUAGE_LABELS = {
    "en": "English",
    "de": "German",
    "ru": "Russian",
    "unknown": "Unknown or unsupported",
}

TARGET_LANGUAGE_CHOICES = [
    ("auto", "Auto (match source language)"),
    ("en", "English"),
    ("de", "German"),
    ("ru", "Russian"),
]

TARGET_LANGUAGE_LABELS = {value: label for value, label in TARGET_LANGUAGE_CHOICES}

TRANSLATE_TO_EN = {
    "de": translate_text_de_to_en,
    "ru": translate_text_ru_to_en,
}

TRANSLATE_FROM_EN = {
    "de": translate_text_en_to_de,
    "ru": translate_text_en_to_ru,
}

EXTRACTORS = {
    "pdf": extract_text_from_pdf,
    "docx": extract_text_from_docx,
    "jpg": extract_text_from_image,
    "jpeg": extract_text_from_image,
    "png": extract_text_from_image,
    "tif": extract_text_from_image,
    "tiff": extract_text_from_image,
}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def label_for_language(code: Optional[str]) -> str:
    if not code:
        return LANGUAGE_LABELS["unknown"]
    return LANGUAGE_LABELS.get(code, LANGUAGE_LABELS["unknown"])


def safe_translate(
    translator: Callable[[str], str],
    text: str,
    success_message: str,
    failure_message: str,
    status_log: List[str],
) -> Tuple[str, bool]:
    try:
        translated_text = translator(text)
    except Exception as exc:  # pragma: no cover - defensive logging
        status_log.append(f"{failure_message}: {exc}")
        return text, False

    status_log.append(success_message)
    return translated_text, True


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["PDF_OUTPUT_FOLDER"] = "static/pdf_outputs"
app.secret_key = os.getenv("FLASK_SECRET_KEY", "docshield-dev")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PDF_OUTPUT_FOLDER"], exist_ok=True)


@app.context_processor
def inject_template_globals():
    return {"target_language_choices": TARGET_LANGUAGE_CHOICES}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_file():
    uploaded_file = request.files.get("file")
    target_language = request.form.get("target_language", "auto")
    generate_pdf = request.form.get("generate_pdf", "on") == "on"

    if not uploaded_file or uploaded_file.filename == "":
        flash("Please choose a document before starting the analysis.", "error")
        return redirect(url_for("index"))

    if not allowed_file(uploaded_file.filename):
        flash("Unsupported file type. Please upload a PDF, DOCX, or image file.", "error")
        return redirect(url_for("index"))

    filename = secure_filename(uploaded_file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    uploaded_file.save(file_path)

    extension = filename.rsplit(".", 1)[1].lower()
    extractor = EXTRACTORS.get(extension)

    if extractor is None:
        flash("We couldn't determine how to process this file type.", "error")
        return redirect(url_for("index"))

    try:
        extracted_text = extractor(file_path)
    except Exception as exc:  # pragma: no cover - defensive logging
        app.logger.exception("Failed to extract text", exc_info=exc)
        flash("An unexpected error occurred while reading your file.", "error")
        return redirect(url_for("index"))
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass

    if not extracted_text or not extracted_text.strip():
        flash("We couldn't find any readable text in that document.", "error")
        return redirect(url_for("index"))

    detected_language: Optional[str] = None
    detection_error: Optional[str] = None
    translation_steps: List[str] = []

    try:
        detected_language = detect(extracted_text)
    except LangDetectException as exc:  # pragma: no cover - depends on runtime input
        detection_error = str(exc)
        translation_steps.append("Unable to confidently detect the document language.")

    analysis_text = extracted_text
    analysis_language = detected_language or "unknown"

    if detected_language in TRANSLATE_TO_EN:
        analysis_text, translated = safe_translate(
            TRANSLATE_TO_EN[detected_language],
            extracted_text,
            f"Translated from {label_for_language(detected_language)} to English for redaction.",
            f"Failed to translate from {label_for_language(detected_language)} to English",
            translation_steps,
        )
        if translated:
            analysis_language = "en"

    cleaned_text, logs = process_text_in_chunks(analysis_text)

    final_text = cleaned_text
    final_language = analysis_language if analysis_language != "unknown" else detected_language or "en"

    if target_language == "auto":
        if detected_language in TRANSLATE_FROM_EN and analysis_language == "en":
            final_text, translated_back = safe_translate(
                TRANSLATE_FROM_EN[detected_language],
                cleaned_text,
                f"Returned the sanitised document to {label_for_language(detected_language)}.",
                f"Failed to translate sanitised text back to {label_for_language(detected_language)}",
                translation_steps,
            )
            if translated_back:
                final_language = detected_language
        else:
            final_language = analysis_language if analysis_language != "unknown" else detected_language or "en"
    elif target_language in TRANSLATE_FROM_EN:
        if analysis_language == "en":
            final_text, translated_target = safe_translate(
                TRANSLATE_FROM_EN[target_language],
                cleaned_text,
                f"Delivered sanitised document in {label_for_language(target_language)} as requested.",
                f"Failed to translate sanitised text to {label_for_language(target_language)}",
                translation_steps,
            )
            if translated_target:
                final_language = target_language
        else:
            translation_steps.append(
                "Skipped final translation because the sanitised text is not available in English."
            )
            final_language = analysis_language if analysis_language != "unknown" else detected_language or "en"
    else:
        final_language = "en"

    pdf_filename = ""
    if generate_pdf:
        try:
            pdf_path = generate_pdf_with_highlights(
                extracted_text, final_text, output_folder=app.config["PDF_OUTPUT_FOLDER"]
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            app.logger.exception("Failed to generate PDF", exc_info=exc)
            translation_steps.append("PDF generation failed; see server logs for details.")
        else:
            pdf_filename = os.path.basename(pdf_path)
            translation_steps.append("Generated a PDF with highlighted redactions.")

    translation_steps.append(
        f"Final output language: {label_for_language(final_language)}."
    )

    stats = {
        "log_count": len(logs),
        "redaction_count": final_text.count("[REDACTED]"),
        "character_count": len(final_text),
    }

    context = {
        "file_name": filename,
        "extracted_text": extracted_text,
        "cleaned_text": cleaned_text,
        "analysis_text": cleaned_text,
        "analysis_language": analysis_language,
        "analysis_language_label": label_for_language(analysis_language),
        "final_text": final_text,
        "final_language": final_language,
        "final_language_label": label_for_language(final_language),
        "logs": logs,
        "translation_steps": translation_steps,
        "detected_language": detected_language,
        "detected_language_label": label_for_language(detected_language),
        "detection_error": detection_error,
        "pdf_filename": pdf_filename,
        "target_language": target_language,
        "target_language_label": TARGET_LANGUAGE_LABELS.get(
            target_language, TARGET_LANGUAGE_LABELS["auto"]
        ),
        "stats": stats,
    }

    return render_template("result.html", **context)


@app.route("/generate_explanation", methods=["POST"])
def generate_explanation_route():
    cleaned_text = request.form["cleaned_text"]
    explanation = generate_explanation(cleaned_text)

    logs = request.form.getlist("logs")
    translation_steps = request.form.getlist("translation_steps")
    extracted_text = request.form.get("extracted_text", "")
    final_text = request.form.get("final_text", cleaned_text)
    analysis_language = request.form.get("analysis_language") or None
    final_language = request.form.get("final_language") or "en"
    detected_language = request.form.get("detected_language") or None
    pdf_filename = request.form.get("pdf_filename", "")
    target_language = request.form.get("target_language", "auto")
    detection_error = request.form.get("detection_error") or None
    file_name = request.form.get("file_name", "Uploaded document")

    stats = {
        "log_count": len(logs),
        "redaction_count": final_text.count("[REDACTED]"),
        "character_count": len(final_text),
    }

    context = {
        "file_name": file_name,
        "extracted_text": extracted_text,
        "cleaned_text": cleaned_text,
        "analysis_text": cleaned_text,
        "analysis_language": analysis_language,
        "analysis_language_label": label_for_language(analysis_language),
        "final_text": final_text,
        "final_language": final_language,
        "final_language_label": label_for_language(final_language),
        "logs": logs,
        "translation_steps": translation_steps,
        "detected_language": detected_language,
        "detected_language_label": label_for_language(detected_language),
        "detection_error": detection_error,
        "pdf_filename": pdf_filename,
        "target_language": target_language,
        "target_language_label": TARGET_LANGUAGE_LABELS.get(
            target_language, TARGET_LANGUAGE_LABELS["auto"]
        ),
        "stats": stats,
        "explanation": explanation,
    }

    return render_template("result.html", **context)


if __name__ == "__main__":
    app.run(debug=True)
