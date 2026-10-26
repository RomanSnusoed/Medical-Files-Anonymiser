# Security model, restrictions and outstanding risks

> **Use synthetic data only.** This is not a compliant medical data processor
> and does not establish legal anonymity under GDPR, HIPAA or any other regime.

## Existing protections

- Request body limit (15 MiB); PDF max 50 pages; text max 200,000 characters;
  image max 10 megapixels; DOCX archive expansion cap 40 MiB.
- Extension validation plus PDF signature/DOCX ZIP/image content validation.
- Isolated temporary upload directory, automatically removed on exit.
- No OCR images or generated PDFs written to the server file system in the web route.
- Random session-bound tokens for downloads. Result data is kept server-side,
  not in signed client cookies or HTML hidden inputs.
- CSRF tokens on upload and external explanation forms.
- Conservative response headers (`Cache-Control: no-store`, CSP,
  `X-Content-Type-Options`, `X-Frame-Options`).
- `LOG_PII=1` has an effect **only** in local Flask debug mode; otherwise
  detector logs show labels and source offsets, not the values.
- External OpenAI call requires both `ENABLE_EXTERNAL_AI=1` and an explicit
  checkbox. Even redacted text may contain residual PII.

## Development vs production configuration

| Behavior | Normal mode | Local debug with `FLASK_DEBUG=1` and `LOG_PII=1` |
|---|---|---|
| Detector values in UI log | No | Yes, synthetic data only |
| Raw extracted text in result UI | No | Yes, synthetic data only |
| Verbose server-side exception values | No | Avoided for uploads |
| Raw file saved beyond request | No | No |
| External explanation | Disabled without separate opt-in | Still disabled without separate opt-in |

The environment variable `FLASK_SECRET_KEY` should be fixed to a strong
random value for any shared instance. `COOKIE_SECURE=1` requires HTTPS.
Flask `debug=True` must **never** be used in an exposed or public service.

## Not implemented / known residual risks

- No user authentication, authorization model beyond per-session isolation,
  audit log, request rate limiting, antivirus scanning or attack isolation.
- Malicious DOCX/PDF parsers or images can still exploit dependency bugs.
  Resource limits mitigate but cannot eliminate decompression/CPU attacks.
- OCR can miss embedded handwriting and image text; rich PDF metadata and
  original layout are not preserved in the reconstructed text-only export.
- The system does not redact PDF byte streams, original attachments, document
  metadata, comments, images or non-extracted text.
- PII detection recall is unknown until real-model evaluation. False
  negatives can remain, and translation can alter personal names.
- Per-process in-memory session cache is unsuitable for horizontal scaling;
  old entries remain in memory until eviction or process exit.
- Failed redaction attempts can be detected when models throw exceptions,
  but missed PII often does not raise an error.
- Existing committed historical outputs may still be accessible via Git history;
  deleting them in a later commit does not rewrite history.

**Do not deploy this code for real patient data without a separate security,
legal/privacy and threat-model review.**
