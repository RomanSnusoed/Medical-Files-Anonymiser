"""Command-line entry point for the synthetic-data portfolio demonstration."""
from __future__ import annotations

import argparse
from pathlib import Path

from langdetect import DetectorFactory, detect

from app import EXTRACTORS, LANGUAGE_LABELS, _anonymize, _validate_file, allowed_file
from pdf_generator import build_pdf_bytes

DetectorFactory.seed = 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Best-effort PII redaction on synthetic medical files")
    parser.add_argument("document", type=Path, help="Synthetic PDF, DOCX or image")
    parser.add_argument("--target", choices=["auto", "en", "de", "ru"], default="auto")
    parser.add_argument("--output", type=Path, help="Optional .txt or .pdf output")
    parser.add_argument(
        "--verbose-logs", action="store_true",
        help="Include detected PII in console logs (synthetic data ONLY)",
    )
    args = parser.parse_args()
    if not args.document.is_file() or not allowed_file(args.document.name):
        parser.error("Document must exist and use a supported extension")
    extension = args.document.suffix.removeprefix(".").lower()
    _validate_file(args.document, extension)
    text = EXTRACTORS[extension](args.document)
    if not text or not text.strip():
        parser.error("Document contains no readable text")
    if len(text) > 200_000:
        parser.error("Document exceeds processing text limit")
    source = detect(text)
    if source not in LANGUAGE_LABELS:
        parser.error("Only English, German and Russian are supported")
    _english, cleaned, _lang, logs, _steps = _anonymize(
        text, source, args.target, verbose=args.verbose_logs
    )
    if args.output:
        if args.output.suffix.lower() == ".pdf":
            args.output.write_bytes(build_pdf_bytes(cleaned))
        elif args.output.suffix.lower() == ".txt":
            args.output.write_text(cleaned, encoding="utf-8")
        else:
            parser.error("--output must end in .txt or .pdf")
        print(f"Output written to {args.output}")
    else:
        print(cleaned)
    if args.verbose_logs:
        print("\nDetector logs (synthetic data ONLY):")
        print("\n".join(logs))
    print("\nNote: Automated redaction does not guarantee anonymity.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
