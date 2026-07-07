from __future__ import annotations

from src.translation.markdown_translator import (
    TRANSLATION_SYSTEM_PROMPT,
    build_translation_messages,
    extract_text,
)


class _MockMessage:
    def __init__(self, content):
        self.content = content


class _MockChoice:
    def __init__(self, content):
        self.message = _MockMessage(content)


class _MockResponse:
    def __init__(self, content):
        self.choices = [_MockChoice(content)]


def test_build_translation_messages_preserves_structure_rules() -> None:
    messages = build_translation_messages("hello")

    assert messages[0]["role"] == "system"
    assert TRANSLATION_SYSTEM_PROMPT in messages[0]["content"]
    assert "preserve all markdown formatting exactly" in messages[0]["content"].lower()
    assert messages[1] == {"role": "user", "content": "hello"}


def test_extract_text_handles_list_content() -> None:
    response = _MockResponse([
        {"type": "text", "text": "Hello"},
        {"type": "text", "text": " world"},
    ])

    assert extract_text(response) == "Hello world"


def test_extract_text_handles_string_content() -> None:
    response = _MockResponse("Hello world")

    assert extract_text(response) == "Hello world"
