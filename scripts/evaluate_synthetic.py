"""Run local models on non-real synthetic data and report a recall proxy."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cleaners import process_text_in_chunks  # noqa: E402

CORPUS = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "synthetic_pii.json"


def main() -> int:
    rows = json.loads(CORPUS.read_text(encoding="utf-8"))
    tested = 0
    removed = 0
    for index, row in enumerate(rows, start=1):
        cleaned, _ = process_text_in_chunks(row["text"], language=row["language"])
        missed = []
        for phrase in row["sensitive_strings"]:
            tested += 1
            if phrase in cleaned:
                missed.append(phrase)
            else:
                removed += 1
        print(f"case {index}: {len(row['sensitive_strings']) - len(missed)} / "
              f"{len(row['sensitive_strings'])} seeded strings removed")
    proxy = removed / tested if tested else 0
    print(f"Synthetic seeded-string removal proxy: {removed}/{tested} = {proxy:.1%}")
    print("This is NOT production-quality PII recall, precision or proof of anonymisation.")
    return 0 if tested and removed == tested else 1


if __name__ == "__main__":
    raise SystemExit(main())
