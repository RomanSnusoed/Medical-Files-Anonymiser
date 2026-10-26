"""Flask UI for a local-first, best-effort medical-document redaction demo.

Not approved to process real patient information. Use synthetic files only.
"""
from __future__ import annotations

import hmac
import io
import os
import secrets
import tempfile
import threading
import time
import zipfile
from pathlib import Path

from flask import (
    Flask, abort, flash, redirect, render_template, request, send_file, session, url_for
)
from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from cleaners import AnonymizationError, process_text_in_chunks
from extractors import extract_text_from_docx, extract_text_from_image, extract_text_from_pdf
from openai_utils import generate_explanation
from pdf_generator import build_pdf_bytes
from translator import translate_preserving_markers

DetectorFactory.seed = 0

ALLOWED_EXTENSIONS = {"pdf", "docx", "jpg", "jpeg", "png", "tif", "tiff"}
LANGUAGE_LABELS = {"en": "English", "de": "German", "ru": "Russian"}
TARGET_LANGUAGE_CHOICES = [
    ("auto", "Auto (match source language)"),
    ("en", "English"),
    ("de", "German"),
    ("ru", "Russian"),
]
EXTRACTORS = {
    "pdf": extract_text_from_pdf,
    "docx": extract_text_from_docx,
    "jpg": extract_text_from_image,
    "jpeg": extract_text_from_image,
    "png": extract_text_from_image,
    "tif": extract_text_from_image,
    "tiff": extract_text_from_image,
}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
JOB_TTL_SECONDS = 20 * 60
MAX_JOBS = 20


class ProcessingError(RuntimeError):
    """A file could not be processed to a safe best-effort result."""


app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
    SEND_FILE_MAX_AGE_DEFAULT=0,
)

# Ephemeral single-process session state; no patient data in cookies or disk.
# A multi-worker deployment would require a secured server-side session store.
_jobs: dict[tuple[str, str], tuple[float, dict]] = {}
_jobs_lock = threading.Lock()


def _csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def _session_id() -> str:
    if "sid" not in session:
        session["sid"] = secrets.token_urlsafe(32)
    return session["sid"]


def _verify_csrf() -> None:
    provided = request.form.get("csrf_token", "")
    if not provided or not hmac.compare_digest(provided, _csrf_token()):
        abort(400, "Invalid form token")


def _store_job(data: dict) -> str:
    sid = _session_id()
    token = secrets.token_urlsafe(32)
    with _jobs_lock:
        now = time.monotonic()
        for key, (expires, _) in list(_jobs.items()):
            if expires < now:
                del _jobs[key]
        if len(_jobs) >= MAX_JOBS:
            del _jobs[min(_jobs, key=lambda key: _jobs[key][0])]
        _jobs[(sid, token)] = (now + JOB_TTL_SECONDS, data)
    return token


def _load_job(token: str) -> dict:
    sid = session.get("sid", "")
    if not sid:
        abort(404)
    with _jobs_lock:
        entry = _jobs.get((sid, token))
        if entry is None:
            abort(404)
        expires, data = entry
        if expires <= time.monotonic():
            del _jobs[(sid, token)]
            abort(410)
        return data


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _validate_file(path: Path, extension: str) -> None:
    """Check actual format, not merely the uploaded filename."""
    if path.stat().st_size == 0:
        raise ProcessingError("The uploaded file is empty.")
    if extension == "pdf":
        if not path.read_bytes()[:5] == b"%PDF-":
            raise ProcessingError("This file is not a valid PDF.")
    elif extension == "docx":
        try:
            with zipfile.ZipFile(path) as archive:
                info = archive.infolist()
                if (
                    len(info) > 1000
                    or sum(member.file_size for member in info) > 40 * 1024 * 1024
                    or "word/document.xml" not in archive.namelist()
                ):
                    raise ProcessingError("Invalid or oversized DOCX archive.")
        except (zipfile.BadZipFile, OSError) as exc:
            raise ProcessingError("Invalid DOCX document.") from exc
    else:
        try:
            with Image.open(path) as image:
                if image.width * image.height > 10_000_000:
                    raise ProcessingError("Image exceeds the 10-megapixel limit.")
                image.verify()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise ProcessingError("Invalid or oversized image.") from exc


def _extract_upload(upload) -> tuple[str, str]:
    filename = secure_filename(upload.filename or "")
    if not filename or not allowed_file(filename):
        raise ProcessingError("Unsupported file type. Use PDF, DOCX, JPG, PNG, or TIFF.")
    extension = filename.rsplit(".", 1)[1].lower()
    # Each request has an isolated temporary directory, removed even on errors.
    with tempfile.TemporaryDirectory(prefix="medfile-") as directory:
        path = Path(directory) / filename
        upload.save(path)
        _validate_file(path, extension)
        text = EXTRACTORS[extension](path)
    if not text or not text.strip():
        raise ProcessingError("No readable text found in this document.")
    if len(text) > MAX_TEXT_CHARS:
        raise ProcessingError("Document text exceeds the 200,000-character limit.")
    return filename, text


def _anonymize(text: str, source: str, target: str, *, verbose: bool):
    """Redact before any translation, then re-check translated English."""
    analysis_text, logs = process_text_in_chunks(text, language=source, include_pii=verbose)
    steps = [f"Initial PII detection on {LANGUAGE_LABELS[source]} source."]
    if source != "en":
        # Preserve redaction placeholders through translation.
        analysis_text = translate_preserving_markers(analysis_text, source, "en")
        steps.append(f"Translated pre-redacted text from {source} to English.")
        analysis_text, second_logs = process_text_in_chunks(
            analysis_text, language="en", include_pii=verbose
        )
        logs += second_logs
        steps.append("Performed second English PII detection pass.")
    delivery_language = source if target == "auto" else target
    final_text = translate_preserving_markers(analysis_text, "en", delivery_language)
    if delivery_language != "en":
        steps.append(f"Translated redacted text to {delivery_language}.")
    return analysis_text, final_text, delivery_language, logs, steps


@app.context_processor
def template_values():
    return {"target_language_choices": TARGET_LANGUAGE_CHOICES, "csrf_token": _csrf_token()}


@app.after_request
def security_headers(response):
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'"
    )
    return response


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    flash("Upload exceeds the 15 MB limit.", "error")
    return redirect(url_for("index")), 303


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_file():
    _verify_csrf()
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        flash("Choose a document first.", "error")
        return redirect(url_for("index")), 303
    target = request.form.get("target_language", "auto")
    if target not in {value for value, _ in TARGET_LANGUAGE_CHOICES}:
        abort(400, "Invalid target language")
    want_pdf = request.form.get("generate_pdf") == "on"
    verbose = app.debug and os.environ.get("LOG_PII") == "1"

    try:
        filename, extracted_text = _extract_upload(uploaded)
        try:
            source_language = detect(extracted_text)
        except LangDetectException as exc:
            raise ProcessingError("Could not detect the document language.") from exc
        if source_language not in LANGUAGE_LABELS:
            raise ProcessingError("Only English, German, and Russian are supported.")
        analysis_text, final_text, final_language, logs, steps = _anonymize(
            extracted_text, source_language, target, verbose=verbose
        )
        pdf_bytes = build_pdf_bytes(final_text) if want_pdf else None
    except (ProcessingError, AnonymizationError, ValueError) as exc:
        # Avoid reflecting exception text from external parsers into client HTML.
        app.logger.warning("Document processing did not complete (%s)", type(exc).__name__)
        flash(str(exc) if isinstance(exc, ProcessingError) else "Processing failed; no output released.", "error")
        return redirect(url_for("index")), 303
    except Exception:
        app.logger.exception("Document processing failed")
        flash("Unexpected processing error; no output released.", "error")
        return redirect(url_for("index")), 303

    token = _store_job({
        "filename": filename,
        "source_language": source_language,
        "analysis_text": analysis_text,
        "final_text": final_text,
        "final_language": final_language,
        "target": target,
        "logs": logs,
        "steps": steps,
        "source_preview": extracted_text if verbose else "",
        "pdf_bytes": pdf_bytes,
        "explanation": "",
    })
    return redirect(url_for("result_page", token=token), code=303)


@app.route("/result/<token>")
def result_page(token):
    job = _load_job(token)
    return render_template(
        "result.html",
        file_name=job["filename"],
        detected_language_label=LANGUAGE_LABELS[job["source_language"]],
        final_language_label=LANGUAGE_LABELS[job["final_language"]],
        target_language_label=(
            "Auto" if job["target"] == "auto" else LANGUAGE_LABELS[job["target"]]
        ),
        extracted_text=job["source_preview"],
        analysis_text=job["analysis_text"],
        final_text=job["final_text"],
        logs=job["logs"],
        translation_steps=job["steps"],
        stats={
            "log_count": len(job["logs"]),
            "redaction_count": job["final_text"].count("[REDACTED]"),
            "character_count": len(job["final_text"]),
        },
        pdf_filename="redacted_report.pdf" if job["pdf_bytes"] is not None else "",
        explanation=job["explanation"],
        token=token,
    )


@app.route("/download/<token>")
def download_pdf(token):
    job = _load_job(token)
    if job["pdf_bytes"] is None:
        abort(404)
    return send_file(
        io.BytesIO(job["pdf_bytes"]),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="redacted_report.pdf",
        max_age=0,
    )


@app.route("/generate_explanation", methods=["POST"])
def generate_explanation_route():
    _verify_csrf()
    token = request.form.get("job_token", "")
    job = _load_job(token)
    if request.form.get("external_api_consent") != "yes":
        flash("Explicit consent is required before sending data to an external API.", "error")
        return redirect(url_for("result_page", token=token)), 303
    if os.environ.get("ENABLE_EXTERNAL_AI") != "1":
        flash("External AI is disabled by default. Enable it only with synthetic data.", "error")
        return redirect(url_for("result_page", token=token)), 303
    try:
        explanation = generate_explanation(job["analysis_text"])
    except Exception:
        app.logger.warning("External AI explanation failed")
        flash("AI explanation unavailable; no result was saved.", "error")
    else:
        with _jobs_lock:
            job["explanation"] = explanation
    return redirect(url_for("result_page", token=token)), 303


if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=os.environ.get("FLASK_DEBUG") == "1")
