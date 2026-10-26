# Architecture and design decisions

## Component map

| Component | Purpose | Key dependency |
|---|---|---|
| `app.py` | Flask routes, validation, isolated uploads, session access, error handling | Flask |
| `extractors.py` | Extract PDF/DOCX and OCR image-only pages | PyMuPDF, Tesseract, python-docx |
| `cleaners.py` | Collect PII spans; reconcile overlaps; replace with markers | Presidio, XLM-R, regex |
| `translator.py` | Cached MarianMT translation, preserving redaction markers | transformers, PyTorch |
| `pdf_generator.py` | Text-only PDF reconstruction in memory | ReportLab |
| `openai_utils.py` | Optional explicit-consent explanation API call | OpenAI |
| `main.py` | CLI entry point; reuses Flask pipeline functions | argparse |

## Detection flow

1. Accept an upload of an allowed type, then verify the actual file signature
   or archive/image structure. Use an isolated temporary directory and delete
   the uploaded file as soon as extraction ends.
2. Detect language. Reject unsupported or unrecognized languages.
3. Run multilingual XLM-R NER and regex over the **original** text.
   For English documents, also use Presidio.
4. If not English, translate the **already-redacted** text to English,
   keeping `[REDACTED]` tokens outside model input; rerun all detectors
   in English. This reduces the risk of names being distorted by translation
   before detection, but does not eliminate missed entities.
5. Transform detected offsets into absolute text spans. Merge overlapping
   spans before applying replacements. The transformer model returns
   `PER`, `LOC` and `ORG` labels; Presidio uses its own labels.
6. Translate the redacted English result to the requested output language.
   Markers never enter the translation model.
7. Store only output text, summary metadata, optional sanitized logs and PDF
   bytes in a **per-process, per-session, 20-minute in-memory store**.

## Failure modes

Required NLP initialization, translation and redaction stages fail closed:
the UI does not produce a report if a stage throws an exception. A failure
to recognize an entity **cannot** be detected by this policy; it remains
the primary risk. Source-language Presidio is intentionally disabled
for German/Russian because the default Presidio NLP configuration is English.

## State and concurrency

- No uploaded documents or OCR page bitmaps are intentionally persisted.
- A random result token is bound to the browser's signed session cookie.
- Download uses a Flask route and never serves generated output via `static/`.
- Session data is **per worker**. This is a single-process demonstration;
  deployments with multiple workers need a secure shared state backend.
- The cache has a 20-minute TTL and a process-level cap of 20 entries.
  Eviction runs on insertion; idle expired objects may remain in memory
  until eviction or process exit.

## Alternatives intentionally not chosen

- Microservices, message queues and Kubernetes: unnecessary operational
  complexity for this limited portfolio demonstration.
- Database persistence of medical documents: increases data-risk surface.
- Automatically posting files to OpenAI: disallowed by design.
- Editing original PDF bytes: not implemented; the export is a new PDF
  constructed from redacted text.
- A "100% anonymous" output assertion: cannot be justified by these models.
