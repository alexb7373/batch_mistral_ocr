"""
Tests for the OCR client wrapper.
"""

from __future__ import annotations

import base64

from src.ocr.client import OCRClient
from src.utils.image_utils import ImageFormat, ImageUtils


def _client_for_test():
    client = OCRClient.__new__(OCRClient)
    client.max_retries = 0
    client.retry_delay = 0
    client.usage_tracker = None
    return client


def test_process_image_preserves_data_url():
    client = _client_for_test()
    captured = {}

    def fake_retry(func, *args, **kwargs):
        captured["image_url"] = kwargs["image_url"]
        return "ok"

    client._retry_on_failure = fake_retry
    data_url = "data:image/png;base64,abcd1234"

    result = client.process_image(data_url)

    assert result == "ok"
    assert captured["image_url"] == data_url


def test_process_image_wraps_raw_base64():
    client = _client_for_test()
    captured = {}

    def fake_retry(func, *args, **kwargs):
        captured["image_url"] = kwargs["image_url"]
        return "ok"

    client._retry_on_failure = fake_retry
    png_data = b"\x89PNG\r\n\x1a\nrest"
    raw_base64 = base64.b64encode(png_data).decode("utf-8")

    result = client.process_image(raw_base64)

    assert result == "ok"
    assert captured["image_url"] == ImageUtils.create_data_url(ImageFormat.PNG.mime_type, raw_base64)


def test_describe_image_preserves_data_url():
    client = _client_for_test()
    captured = {}

    def fake_retry(func, *args, **kwargs):
        captured["image_url"] = kwargs["image_url"]
        captured["prompt"] = kwargs["prompt"]
        captured["model"] = kwargs["model"]
        return type(
            "Response",
            (),
            {"choices": [type("Choice", (), {"message": type("Msg", (), {"content": "diagram"})()})()]},
        )()

    client._retry_on_failure = fake_retry
    data_url = "data:image/png;base64,abcd1234"

    result = client.describe_image(data_url, prompt="Explain the image")

    assert result == "diagram"
    assert captured["image_url"] == data_url
    assert captured["prompt"] == "Explain the image"
    assert captured["model"] == "pixtral-12b-2409"


def test_describe_image_wraps_raw_base64():
    client = _client_for_test()
    captured = {}

    def fake_retry(func, *args, **kwargs):
        captured["image_url"] = kwargs["image_url"]
        return type(
            "Response",
            (),
            {"choices": [type("Choice", (), {"message": type("Msg", (), {"content": "diagram"})()})()]},
        )()

    client._retry_on_failure = fake_retry
    png_data = b"\x89PNG\r\n\x1a\nrest"
    raw_base64 = base64.b64encode(png_data).decode("utf-8")

    result = client.describe_image(raw_base64, prompt="Explain the image")

    assert result == "diagram"
    assert captured["image_url"] == ImageUtils.create_data_url(ImageFormat.PNG.mime_type, raw_base64)
