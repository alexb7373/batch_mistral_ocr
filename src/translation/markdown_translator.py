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
PAGE_SPLIT_RE = re.compile(r"(?m)^<!-- page \d+ -->\s*$")
BARE_PAGE_NUMBER_RE = re.compile(r"^\d+$")
IMAGE_ONLY_LINE_RE = re.compile(r"^!\[[^\]]*\]\([^)]+\)$")


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
    """Translate a markdown document using a chat model.

    The document is translated page-by-page when it contains OCR page markers,
    which keeps the original boundaries intact and reduces the risk of page
    markers being dropped or merged by the model.
    """
    if PAGE_MARKER_RE.search(markdown):
        return translate_markdown_by_page(markdown, client, model=model)

    response = client.chat.complete(
        model=model,
        messages=build_translation_messages(markdown),
    )
    return extract_text(response)


def _split_page_sections(markdown: str) -> list[tuple[str | None, str]]:
    """Split OCR markdown into page marker + body sections.

    Returns a list of (page_marker, body) tuples. The first tuple may have
    page_marker=None if the document contains leading non-paged content.
    """
    matches = list(PAGE_SPLIT_RE.finditer(markdown))
    if not matches:
        return [(None, markdown)]

    sections: list[tuple[str | None, str]] = []
    prefix = markdown[: matches[0].start()]
    if prefix.strip():
        sections.append((None, prefix))

    for idx, match in enumerate(matches):
        marker = match.group(0).strip()
        body_start = match.end()
        body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        body = markdown[body_start:body_end]
        sections.append((marker, body))

    return sections


def translate_markdown_by_page(
    markdown: str,
    client: Mistral,
    *,
    model: str = "mistral-small-latest",
) -> str:
    """Translate a markdown document page-by-page while preserving markers."""
    translated_parts: list[str] = []

    for page_marker, body in _split_page_sections(markdown):
        if page_marker is None:
            translated = translate_markdown(body, client, model=model)
            if translated:
                translated_parts.append(translated)
            continue

        translated_body = ""
        if body.strip():
            response = client.chat.complete(
                model=model,
                messages=build_translation_messages(body),
            )
            translated_body = extract_text(response)

        translated_parts.append(page_marker)
        if translated_body:
            translated_parts.append(translated_body)

    return "\n\n".join(part.strip() for part in translated_parts if part.strip()).strip()


def clean_translated_markdown(markdown: str) -> str:
    """Remove OCR noise that is not useful for GitHub or Word output.

    Keeps page markers intact, but drops bare page numbers and image-only lines
    that typically come from OCR layout artifacts.
    """
    cleaned_lines: list[str] = []

    for line in markdown.splitlines():
        stripped = line.strip()

        if not stripped:
            cleaned_lines.append("")
            continue

        if BARE_PAGE_NUMBER_RE.fullmatch(stripped):
            continue

        if IMAGE_ONLY_LINE_RE.fullmatch(stripped):
            continue

        cleaned_lines.append(line.rstrip())

    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def translate_markdown_file(
    input_path: Path,
    output_path: Path,
    client: Mistral,
    *,
    model: str = "mistral-small-latest",
) -> Path:
    """Translate a markdown file and write the result to disk."""
    markdown = input_path.read_text(encoding="utf-8")
    translated = clean_translated_markdown(
        translate_markdown(markdown, client, model=model)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(translated.rstrip() + "\n", encoding="utf-8")
    return output_path
