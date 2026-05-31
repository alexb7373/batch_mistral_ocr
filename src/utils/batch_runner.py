"""
Shared batch-processing helpers for OCR entrypoints.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from src.config.settings import AppConfig
from src.ocr.client import OCRClient
from src.ocr.processors import PDFProcessor
from src.utils.logging import ProgressTracker
from src.utils.usage_tracker import UsageTracker


@dataclass
class BatchRunResult:
    """Result of a batch OCR run."""

    rag_targets: list[Path] = field(default_factory=list)


def register_for_rag(markdown_path: Path, rag_dir: Path) -> Path:
    """Copy generated markdown and extracted images into a RAG directory."""
    rag_dir.mkdir(parents=True, exist_ok=True)
    target = rag_dir / markdown_path.name
    shutil.copy2(markdown_path, target)

    image_dir = markdown_path.parent / markdown_path.stem
    if image_dir.exists():
        shutil.copytree(image_dir, rag_dir / image_dir.name, dirs_exist_ok=True)

    return target


def run_pdf_batch(
    pdfs: Iterable[Path],
    config: AppConfig,
    client: OCRClient,
    *,
    run_name: str,
    runtime_dir: Optional[Path] = None,
    register_rag_targets: bool = False,
    rag_dir: Optional[Path] = None,
    usage_tracker: Optional[UsageTracker] = None,
) -> BatchRunResult:
    """Run the standard PDF batch pipeline for a collection of PDFs."""
    pdf_list = [Path(pdf).resolve() for pdf in pdfs]
    progress_tracker = ProgressTracker(
        verbose=config.verbose,
        run_name=run_name,
        runtime_dir=runtime_dir,
    )
    progress_tracker.start()
    progress_tracker.set_input_output(
        str(config.input_dir.absolute()),
        str(config.output_dir.absolute()),
    )
    progress_tracker.set_total(len(pdf_list))

    processor = PDFProcessor(client, config, progress_tracker=progress_tracker)
    rag_targets: list[Path] = []

    for pdf_path in sorted(pdf_list):
        progress_tracker.start_file(pdf_path.name)
        result = processor.process(pdf_path)

        if result.success:
            if result.skipped:
                progress_tracker.skip_file(pdf_path.name)
            else:
                progress_tracker.complete_file(pdf_path.name, success=True)

            if (
                register_rag_targets
                and rag_dir is not None
                and result.output_path is not None
            ):
                rag_targets.append(register_for_rag(result.output_path, rag_dir))
        else:
            progress_tracker.complete_file(pdf_path.name, success=False)
            if result.error:
                progress_tracker.error(f"{pdf_path.name}: {result.error}")

    progress_tracker.print_summary()

    if usage_tracker is not None:
        usage_tracker.end()
        usage_tracker.print_summary()
        usage_tracker.save_to_file(config.output_dir / "usage_stats.json")

    return BatchRunResult(rag_targets=rag_targets)
