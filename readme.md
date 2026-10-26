# Medical Files Anonymiser

A **local-first Applied AI / software engineering portfolio prototype** for exploring
best-effort medical document PII detection and text redaction.

> **Research/demo software, not a medical product.** Use **synthetic documents only**.
> No NLP model guarantees complete removal of personal information. Outputs require
> human review and are **not automatically safe to share**. No claim of GDPR or
> HIPAA compliance is made.

## Capabilities

- Extract embedded text from PDFs; OCR image-only PDF pages and JPG/PNG/TIFF
  images using Tesseract. Extract DOCX paragraphs, tables, headers and footers.
- Detect English, German and Russian.
- Combine Microsoft Presidio (English), multilingual XLM-RoBERTa NER, and
  regex recognizers for PII. Merge overlapping spans **before** redaction.
- For German/Russian, redact source text **before** translation, translate
  redacted content to English, and run an additional English detection pass.
- Convert the reviewed text into a **new text-only PDF** with colored
  `[REDACTED]` markers. The original PDF is **not modified**.
- Optionally explain *synthetic* medical text through the OpenAI API.
  API calls are disabled unless explicitly enabled and consented to.

## Architecture

```text
Flask upload (15 MB) -> validate format -> isolated temporary file
       |
PDF / DOCX / Tesseract extraction -> detect language
       |
PII detectors: multilingual XLM-R + regex (+ Presidio for English)
       |
English source? ------------------------ yes -------------------+
       | no                                                     |
Translate pre-redacted text to English                         |
       |                                                        |
Second pass: Presidio + XLM-R + regex                           |
       +--------------------------------------------------------+
       |
Translate redacted English to requested language
       |
Ephemeral session-bound result (20 min, one Python process)
       |
Browser review + memory-generated PDF download
       |
Explicit opt-in to optional external OpenAI explanation
```

More details: [Architecture](docs/ARCHITECTURE.md),
[Security/limitations](docs/SECURITY.md), and
[Testing and evaluation](docs/TESTING.md).

## Local setup (Python 3.11 recommended)

### Windows / VS Code (PowerShell)

```powershell
git clone https://github.com/RomanSnusoed/Medical-Files-Anonymiser.git
cd Medical-Files-Anonymiser
git switch fix/redaction-overlap

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install **Tesseract OCR** separately and ensure `tesseract --version`
works. If necessary, set `$env:TESSERACT_CMD` to the full executable path.

**Presidio/spaCy:** install the English language model required by the
Presidio NLP engine, for example:

```powershell
python -m spacy download en_core_web_lg
```

The first run also downloads Hugging Face NER and translation weights.
They require network access and available disk/RAM. GPU is optional.
If a required model fails to initialize, the processing request fails
instead of returning a misleadingly anonymized document.

**Unicode PDF:** ReportLab requires a Unicode TrueType font.
On Windows, the usual Arial font is detected. If none is found:

```powershell
$env:PDF_FONT_PATH="C:\Windows\Fonts\arial.ttf"
```

### Run the web demo

```powershell
$env:FLASK_SECRET_KEY="choose-a-long-random-local-secret"
python app.py
```

Open http://127.0.0.1:5000 and upload **only synthetic test files**.
Do not expose the Flask development server on a public interface.

### Optional development logging

PII values are **not logged by default**. For local debugging with
**synthetic inputs only**, enable both flags:

```powershell
$env:FLASK_DEBUG="1"
$env:LOG_PII="1"
python app.py
```

This also shows extracted source text in the result page. Never use
this mode with real patient information or on a public server.
Disable both flags when finished.

### Optional external AI

External AI is disabled by default. To enable it on **synthetic data only**:

```powershell
$env:ENABLE_EXTERNAL_AI="1"
$env:OPENAI_API_KEY="your-own-key"
$env:OPENAI_MODEL="gpt-4o-mini"
python app.py
```

The browser also requires explicit consent before sending the processed
English text. **Do not assume redaction makes data safe to transmit.**

### CLI

```powershell
python main.py synthetic-report.pdf --target en --output synthetic-redacted.pdf
python main.py synthetic-report.docx --target auto --output synthetic.txt
```

`--verbose-logs` prints detected values and is for local synthetic data only.

## Tests and CI

Fast unit/integration tests use mocks for heavy NLP models:

```powershell
python -m pip install -r requirements-ci.txt
python -m pytest tests -q
python -m compileall -q .
ruff check --select E4,E7,E9,F .
```

GitHub Actions runs the same lightweight checks. **Passing CI does not
demonstrate the actual accuracy of Presidio, NER, MarianMT, or OCR.**
For a real-model synthetic assessment, see [Testing](docs/TESTING.md).

## Known limitations

- Entity-based NLP can miss PHI; some false positives are unavoidable.
- Language identification may fail on short documents.
- Translation may alter meaning and require review.
- OCR quality depends on the scanned source and page layout.
- PDF output is reconstructed text, not a cryptographically redacted original.
- Process-memory results expire after 20 minutes; multi-worker deployment,
  real user authentication, rate limiting and audited PHI controls are **not**
  implemented.
- External explanations are not diagnoses or medical advice.

## Project origin

A refactored personal portfolio demonstration inspired by document-processing
work. The published repository is a software prototype, not an authorized
production deployment or an endorsement by any healthcare organization.

## License

No open-source license has been assigned. Contact the repository owner
before redistributing or incorporating this code into another product.
