from __future__ import annotations

from src.translation.markdown_translator import (
    clean_translated_markdown,
    TRANSLATION_SYSTEM_PROMPT,
    build_translation_messages,
    extract_text,
    translate_markdown,
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


class _FakeChat:
    def __init__(self):
        self.calls = []

    def complete(self, *, model, messages):
        self.calls.append({"model": model, "messages": messages})
        body = messages[-1]["content"]
        return _MockResponse(body.upper())


class _FakeClient:
    def __init__(self):
        self.chat = _FakeChat()


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


def test_translate_markdown_preserves_page_markers() -> None:
    client = _FakeClient()
    markdown = """<!-- page 0 -->
hello

<!-- page 1 -->
world
"""

    translated = translate_markdown(markdown, client)

    assert translated.count("<!-- page 0 -->") == 1
    assert translated.count("<!-- page 1 -->") == 1
    assert "HELLO" in translated
    assert "WORLD" in translated
    assert len(client.chat.calls) == 2


def test_clean_translated_markdown_removes_bare_page_numbers_and_images() -> None:
    markdown = """<!-- page 3 -->
12
![img-0.jpeg](img-0.jpeg)
Actual content
"""

    cleaned = clean_translated_markdown(markdown)

    assert "<!-- page 3 -->" in cleaned
    assert "12" not in cleaned
    assert "img-0.jpeg" not in cleaned
    assert "Actual content" in cleaned
