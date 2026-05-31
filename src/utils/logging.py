"""
Progress tracking and logging utilities for Mistral OCR Batch Processor.
"""

import sys
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProcessingStats:
    """Processing statistics for the entire batch.
    
    Attributes:
        total: Total number of PDFs to process
        succeeded: Number of PDFs processed successfully
        failed: Number of PDFs that failed
        skipped: Number of PDFs skipped
        images_extracted: Number of images extracted from PDFs
        diagrams_extracted: Number of diagrams extracted from images
        start_time: When processing started
    """
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    images_extracted: int = 0
    diagrams_extracted: int = 0
    start_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.succeeded / self.total) * 100
    
    @property
    def duration(self) -> str:
        """Calculate duration as formatted string."""
        if not self.start_time:
            return "0:00:00"
        duration = datetime.now() - self.start_time
        days = duration.days
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if days > 0:
            return f"{days}d {hours}:{minutes:02d}:{seconds:02d}"
        return f"{hours}:{minutes:02d}:{seconds:02d}"


class ProgressTracker:
    """Track and report processing progress.
    
    Provides verbose logging of processing status and collects statistics
    for a final summary report.
    
    Attributes:
        stats: Processing statistics
        verbose: Whether to print progress messages
    """
    
    def __init__(self, verbose: bool = True):
        """Initialize progress tracker.
        
        Args:
            verbose: Whether to show verbose output (default: True)
        """
        self.stats = ProcessingStats()
        self.verbose = verbose
        self._current_file: Optional[str] = None
    
    def start(self):
        """Start processing batch."""
        self.stats.start_time = datetime.now()
        if self.verbose:
            print("=" * 60)
            print("🚀 Mistral OCR Batch Processor")
            print("=" * 60)
    
    def set_total(self, total: int):
        """Set total number of files to process.
        
        Args:
            total: Total number of PDFs
        """
        self.stats.total = total
        if self.verbose:
            print(f"📚 Found {total} PDF(s) to process\n")
    
    def set_input_output(self, input_dir: str, output_dir: str):
        """Display input and output directories.
        
        Args:
            input_dir: Input directory path
            output_dir: Output directory path
        """
        if self.verbose:
            print(f"Input:  {input_dir}")
            print(f"Output: {output_dir}")
            print()
    
    def start_file(self, filename: str):
        """Start processing a file.
        
        Args:
            filename: Name of the file being processed
        """
        self._current_file = filename
        if self.verbose:
            print(f"🔍 Processing {filename}")
    
    def complete_file(self, filename: str, success: bool = True):
        """Complete processing a file.
        
        Args:
            filename: Name of the file
            success: Whether processing succeeded (default: True)
        """
        if success:
            self.stats.succeeded += 1
            if self.verbose:
                print(f"✅ Saved: {filename}")
        else:
            self.stats.failed += 1
    
    def skip_file(self, filename: str):
        """Skip a file (already processed).
        
        Args:
            filename: Name of the file being skipped
        """
        self.stats.skipped += 1
        if self.verbose:
            print(f"⏭️  Skipping {filename}, already processed.")
    
    def extracted_image(self, filename: str):
        """Record image extraction.
        
        Args:
            filename: Name of the extracted image
        """
        self.stats.images_extracted += 1
        if self.verbose:
            print(f"  🖼️  Saved image: {filename}")
    
    def extracted_diagram(self, filename: str, model: str):
        """Record diagram extraction.
        
        Args:
            filename: Name of the image containing the diagram
            model: OCR model used for extraction
        """
        self.stats.diagrams_extracted += 1
        if self.verbose:
            print(f"  📊 Extracted diagram from {filename} using {model}")
    
    def error(self, message: str):
        """Log an error message.
        
        Args:
            message: Error message to display
        """
        if self.verbose:
            print(f"❌ {message}")
    
    def warning(self, message: str):
        """Log a warning message.
        
        Args:
            message: Warning message to display
        """
        if self.verbose:
            print(f"⚠️  {message}")
    
    def info(self, message: str):
        """Log an info message.
        
        Args:
            message: Info message to display
        """
        if self.verbose:
            print(f"ℹ️  {message}")
    
    def print_summary(self):
        """Print processing summary."""
        if not self.verbose:
            return
        
        print()
        print("=" * 60)
        print("📊 Processing Summary")
        print("=" * 60)
        print(f"Total PDFs found:    {self.stats.total}")
        print(f"✅ Processed:        {self.stats.succeeded}")
        print(f"⏭️  Skipped:         {self.stats.skipped}")
        print(f"❌ Failed:           {self.stats.failed}")
        print(f"🖼️  Images extracted: {self.stats.images_extracted}")
        print(f"📊 Diagrams extracted: {self.stats.diagrams_extracted}")
        print(f"⏱️  Duration:         {self.stats.duration}")
        print(f"📈 Success rate:     {self.stats.success_rate:.1f}%")
        
        if self.stats.failed > 0:
            print("\n⚠️  Some files failed. Check the error messages above.")
        
        print("\nDone! ✨")
