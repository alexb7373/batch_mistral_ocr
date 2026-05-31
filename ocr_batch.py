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
from src.utils.usage_tracker import UsageTracker


def main():
    """Main entry point for the OCR batch processor."""
    try:
        # Load configuration
        config = load_config()
        
        # Initialize progress tracker
        progress_tracker = ProgressTracker(verbose=config.verbose, run_name="ocr_batch")
        progress_tracker.start()
        progress_tracker.set_input_output(
            str(config.input_dir.absolute()),
            str(config.output_dir.absolute())
        )
        
        # Initialize usage tracker
        usage_tracker = UsageTracker()
        usage_tracker.start()
        
        # Initialize OCR client with usage tracking
        client = OCRClient(
            api_key=config.api_key,
            max_retries=config.max_retries,
            usage_tracker=usage_tracker
        )
        
        # Initialize PDF processor
        processor = PDFProcessor(client, config, progress_tracker=progress_tracker)
        
        # Find all PDF files in input directory
        pdf_files = list(config.input_dir.glob("*.pdf"))
        progress_tracker.set_total(len(pdf_files))
        
        if not pdf_files:
            progress_tracker.error("No PDF files found in input directory.")
            return
        
        # Process each PDF
        for pdf_file in sorted(pdf_files):
            filename = pdf_file.name
            progress_tracker.start_file(filename)
            
            try:
                result = processor.process(pdf_file)
                
                if result.success:
                    if hasattr(result, 'skipped') and result.skipped:
                        progress_tracker.skip_file(filename)
                    else:
                        progress_tracker.complete_file(filename, success=True)
                else:
                    progress_tracker.complete_file(filename, success=False)
                    if result.error:
                        progress_tracker.error(f"{filename}: {result.error}")
                
            except Exception as e:
                progress_tracker.complete_file(filename, success=False)
                progress_tracker.error(f"{filename}: {str(e)}")
        
        # End usage tracking
        usage_tracker.end()
        
        # Print summaries
        progress_tracker.print_summary()
        usage_tracker.print_summary()
        
        # Save usage to file
        usage_tracker.save_to_file(config.output_dir / "usage_stats.json")
        
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
