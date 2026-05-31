#!/usr/bin/env python3
"""
Batch OCR processor for PDF documents using Mistral OCR API.

This script processes PDF documents, extracts Markdown per page, and handles
embedded images by saving them and performing OCR on those as well.

Usage:
    python ocr_batch.py

Configuration:
    - Set MISTRAL_API_KEY in environment or .env file
    - Create config/config.py for custom input/output directories
    - Or use default directories: pdfs/ for input, output/ for output
"""

import sys
from pathlib import Path

# Add project root to Python path so src is a proper package
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import load_config
from src.ocr.client import OCRClient
from src.ocr.processors import PDFProcessor
from src.utils.logging import ProgressTracker


def main():
    """Main entry point for the OCR batch processor."""
    try:
        # Load configuration
        config = load_config()
        
        # Initialize progress tracker
        tracker = ProgressTracker(verbose=config.verbose)
        tracker.start()
        tracker.set_input_output(
            str(config.input_dir.absolute()),
            str(config.output_dir.absolute())
        )
        
        # Initialize OCR client
        client = OCRClient(
            api_key=config.api_key,
            max_retries=config.max_retries
        )
        
        # Initialize PDF processor
        processor = PDFProcessor(client, config)
        
        # Find all PDF files in input directory
        pdf_files = list(config.input_dir.glob("*.pdf"))
        tracker.set_total(len(pdf_files))
        
        if not pdf_files:
            tracker.error("No PDF files found in input directory.")
            return
        
        # Process each PDF
        for pdf_file in sorted(pdf_files):
            filename = pdf_file.name
            tracker.start_file(filename)
            
            try:
                result = processor.process(pdf_file)
                
                if result.success:
                    if hasattr(result, 'skipped') and result.skipped:
                        tracker.skip_file(filename)
                    else:
                        tracker.complete_file(filename, success=True)
                else:
                    tracker.complete_file(filename, success=False)
                    if result.error:
                        tracker.error(f"{filename}: {result.error}")
                
            except Exception as e:
                tracker.complete_file(filename, success=False)
                tracker.error(f"{filename}: {str(e)}")
        
        # Print summary
        tracker.print_summary()
        
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
