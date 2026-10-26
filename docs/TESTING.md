# Testing and validation

## Fast checks (used in GitHub Actions)

```bash
python -m pip install -r requirements-ci.txt
python -m compileall -q .
ruff check --select E4,E7,E9,F .
python -m pytest tests -q
```

The `requirements-ci.txt` profile intentionally does **not** install large
language models. Unit tests fake/mimic NER and Presidio predictions so
they are deterministic; they do **not** validate real PII recall.

## Local real-model smoke test

After full setup including spaCy model, Tesseract and Hugging Face weights,
run with synthetic data only:

```bash
python main.py demo/synthetic-report.txt
```

Note: the CLI supports PDF, DOCX and images, **not** plain .txt input.
Convert the synthetic text into a DOCX or PDF before running the command,
or use the in-memory quality evaluation script below.

Check that the application handles each type:
- English DOCX with text, header, table and synthetic contact details.
- German/Russian text for translation and pre-redaction.
- Mixed PDF: embedded text on one page and a scan on another.
- Low quality image with rotated text (manually review OCR).
- Invalid files, >15 MiB uploads, overlarge DOCX ZIP and unsupported language.
- Two separate browser sessions: one cannot download the other's output.
- External API stays disabled until explicit configuration and checkbox.

## Synthetic PII recall proxy

```bash
python scripts/evaluate_synthetic.py
```

This loads `tests/fixtures/synthetic_pii.json` and executes **real**
local NLP models. It reports the fraction of seeded synthetic strings no
longer appearing in the output, **not** production-quality NER recall or
precision. Real accuracy evaluation would require annotated spans, a larger
representative multilingual dataset, and false-positive analysis. No
numerical accuracy claim is made until the script is run.

For reproducibility, document model revisions, Python dependencies,
language model versions, CPU/GPU, and any OCR/translation changes.
