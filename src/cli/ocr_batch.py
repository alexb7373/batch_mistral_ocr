#!/usr/bin/env python3
"""Batch OCR processor for PDF documents using the shared pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

from src.config.settings import load_config
from src.ocr.client import OCRClient
from src.utils.batch_runner import run_pdf_batch
from src.utils.usage_tracker import UsageTracker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    """Main entry point for the OCR batch processor."""
    try:
        config = load_config()
        usage_tracker = UsageTracker()
        usage_tracker.start()

        client = OCRClient(
            api_key=config.api_key,
            max_retries=config.max_retries,
            usage_tracker=usage_tracker,
        )

        pdf_files = sorted(config.input_dir.glob("*.pdf"))
        if not pdf_files:
            print("No PDF files found in input directory.")
            return 1

        run_pdf_batch(
            pdf_files,
            config,
            client,
            run_name="ocr_batch",
            usage_tracker=usage_tracker,
        )
        return 0
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user. Exiting...")
        return 1
    except Exception as exc:
        print(f"\n❌ Fatal error: {exc}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

