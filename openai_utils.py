"""Optional OpenAI explanation; never call this with unredacted documents."""
from __future__ import annotations

import os


def generate_explanation(cleaned_text: str) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")
    from openai import OpenAI

    client = OpenAI(timeout=30, max_retries=1)
    result = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {
                "role": "system",
                "content": (
                    "Explain medical terminology in plain language. "
                    "Do not diagnose or offer personal medical advice. "
                    "The input may still contain sensitive data."
                ),
            },
            {"role": "user", "content": cleaned_text[:20000]},
        ],
        max_tokens=1000,
    )
    return result.choices[0].message.content or ""
