#!/usr/bin/env python3
"""Batch OCR processor for PDF documents using the shared pipeline."""

import sys
from pathlib import Path

# Add project root to Python path so src is a proper package
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import load_config
from src.utils.batch_runner import run_pdf_batch
from src.ocr.client import OCRClient
from src.utils.usage_tracker import UsageTracker


def main():
    """Main entry point for the OCR batch processor."""
    try:
        # Load configuration
        config = load_config()
        
        # Initialize usage tracker
        usage_tracker = UsageTracker()
        usage_tracker.start()
        
        # Initialize OCR client with usage tracking
        client = OCRClient(
            api_key=config.api_key,
            max_retries=config.max_retries,
            usage_tracker=usage_tracker
        )

        pdf_files = sorted(config.input_dir.glob("*.pdf"))
        if not pdf_files:
            print("No PDF files found in input directory.")
            return

        run_pdf_batch(
            pdf_files,
            config,
            client,
            run_name="ocr_batch",
            usage_tracker=usage_tracker,
        )
        
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
