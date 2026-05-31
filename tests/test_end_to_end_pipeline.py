"""
Live end-to-end OCR pipeline tests.

These tests are opt-in because they call the Mistral API and can incur cost.
Enable them by setting RUN_LIVE_OCR_TESTS=1 and providing MISTRAL_API_KEY.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.config.settings import AppConfig, load_api_key
from src.ocr.client import OCRClient
from src.ocr.processors import ImageProcessor, PDFProcessor
from src.utils.runtime_manifest import RuntimeManifest

ARTIFACT_ROOT = Path(__file__).parent / "live-ocr-output"


def _require_live_ocr() -> str:
    if os.getenv("RUN_LIVE_OCR_TESTS") != "1":
        pytest.skip("Live OCR tests are disabled. Set RUN_LIVE_OCR_TESTS=1 to enable.")

    try:
        return load_api_key()
    except Exception as exc:
        pytest.skip(f"Live OCR tests require MISTRAL_API_KEY: {exc}")


def _test_pdf_path(project_root: Path) -> Path:
    pdf_path = project_root / "tests" / "pdf" / "Refactoring Code to Load a Document.pdf"
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")
    return pdf_path


def _test_image_path(project_root: Path) -> Path:
    image_path = (
        project_root
        / "tests"
        / "live-ocr-output"
        / "single-pdf"
        / "output"
        / "Refactoring Code to Load a Document"
        / "page004_image0.jpeg"
    )
    if not image_path.exists():
        pytest.skip(f"Test image not found: {image_path}")
    return image_path


def _prepare_artifact_dir(*parts: str) -> Path:
    artifact_dir = ARTIFACT_ROOT.joinpath(*parts)
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def _assert_image_processing_present(markdown_path: Path) -> None:
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "**Vision Extracted" in markdown
    assert "**OCR Extracted" in markdown
    assert "page004_image0.jpeg" in markdown
    assert "page004_image1.jpeg" in markdown
    assert "classDiagram" in markdown or "graph TD" in markdown


def test_live_pipeline_single_pdf(project_root: Path) -> None:
    """Run the full OCR pipeline against one PDF file."""
    api_key = _require_live_ocr()
    source_pdf = _test_pdf_path(project_root)

    output_dir = _prepare_artifact_dir("single-pdf", "output")
    config = AppConfig(
        input_dir=source_pdf.parent,
        output_dir=output_dir,
        api_key=api_key,
        force_reprocess=True,
        verbose=False,
    )
    client = OCRClient(api_key=api_key, max_retries=2)
    processor = PDFProcessor(client, config)

    result = processor.process(source_pdf)

    assert result.success is True
    assert result.output_path is not None
    assert result.output_path.exists()
    assert result.pages_processed > 0
    assert result.output_path.read_text(encoding="utf-8").strip()
    _assert_image_processing_present(result.output_path)

    image_dir = output_dir / source_pdf.stem
    if result.images_processed > 0:
        assert image_dir.exists()


def test_live_single_image(project_root: Path) -> None:
    """Run the standalone image OCR pipeline on one extracted image."""
    api_key = _require_live_ocr()
    image_path = _test_image_path(project_root)

    output_dir = _prepare_artifact_dir("single-image")
    runtime_manifest = RuntimeManifest(
        run_name="single_image",
        root_dir=project_root / "runtime",
    )
    runtime_manifest.record("start", image=str(image_path))

    client = OCRClient(api_key=api_key, max_retries=2)
    processor = ImageProcessor(client)
    result = processor.process(image_path) or ""

    out_path = output_dir / f"{image_path.stem}.md"
    out_path.write_text(
        "\n".join(
            [
                f"# OCR Output for {image_path.name}",
                "",
                "```text",
                result.strip(),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    runtime_manifest.record(
        "complete",
        image=str(image_path),
        output_path=str(out_path),
        output_length=len(result.strip()),
    )

    assert out_path.exists()
    assert result.strip()
    assert result.strip() != "!"
    assert "classDiagram" in result or "graph TD" in result or "Document" in result


def test_live_pipeline_folder_cli(project_root: Path) -> None:
    """Run the folder-oriented CLI pipeline over the tests/pdf directory."""
    api_key = _require_live_ocr()
    source_dir = project_root / "tests" / "pdf"
    source_pdf = _test_pdf_path(project_root)

    output_dir = _prepare_artifact_dir("folder-cli", "output")

    env = os.environ.copy()
    env["MISTRAL_API_KEY"] = api_key

    completed = subprocess.run(
        [
            sys.executable,
            str(project_root / "book_ocr.py"),
            "--books-dir",
            str(source_dir),
            "--output-dir",
            str(output_dir),
            "--all",
            "--quiet",
        ],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        pytest.fail(
            "book_ocr.py failed\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    markdown_path = output_dir / f"{source_pdf.stem}.md"
    assert markdown_path.exists()
    assert markdown_path.read_text(encoding="utf-8").strip()
    _assert_image_processing_present(markdown_path)
