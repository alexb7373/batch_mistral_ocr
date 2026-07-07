"""
Utilities for translating OCR markdown while preserving structure.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mistralai.client import Mistral


TRANSLATION_SYSTEM_PROMPT = (
    "You are a precise document translator. "
    "Translate the user's markdown from Ukrainian to English. "
    "Preserve all Markdown formatting exactly, including headings, bullets, numbering, "
    "links, inline code, fenced code blocks, page markers, and tables. "
    "Preserve LaTeX math and equation syntax exactly, including inline math and display math. "
    "Do not add commentary, explanations, or notes. "
    "Return only the translated markdown."
)

PAGE_MARKER_RE = re.compile(r"^<!-- page \d+ -->$", re.MULTILINE)


def build_translation_messages(markdown: str) -> list[dict[str, str]]:
    """Build the chat messages used for the translation request."""
    return [
        {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
        {"role": "user", "content": markdown},
    ]


def extract_text(response: Any) -> str:
    """Extract plain text from a Mistral chat completion response."""
    try:
        content = response.choices[0].message.content
    except Exception:
        return ""

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "".join(parts).strip()

    return str(content).strip()


def translate_markdown(
    markdown: str,
    client: Mistral,
    *,
    model: str = "mistral-small-latest",
) -> str:
    """Translate a markdown document using a chat model."""
    response = client.chat.complete(
        model=model,
        messages=build_translation_messages(markdown),
    )
    return extract_text(response)


def translate_markdown_file(
    input_path: Path,
    output_path: Path,
    client: Mistral,
    *,
    model: str = "mistral-small-latest",
) -> Path:
    """Translate a markdown file and write the result to disk."""
    markdown = input_path.read_text(encoding="utf-8")
    translated = translate_markdown(markdown, client, model=model)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(translated.rstrip() + "\n", encoding="utf-8")
    return output_path

