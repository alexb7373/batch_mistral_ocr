"""
Progress tracking and runtime manifest utilities for Mistral OCR Batch Processor.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .runtime_manifest import RuntimeManifest


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
    """Track processing progress and write it to a runtime manifest."""

    def __init__(
        self,
        verbose: bool = True,
        run_name: str = "ocr_batch",
        runtime_dir: Optional[Path] = None,
    ):
        self.stats = ProcessingStats()
        self._current_file: Optional[str] = None
        self.verbose = verbose
        self.manifest = RuntimeManifest(run_name=run_name, root_dir=runtime_dir)
    
    def start(self):
        """Start processing batch."""
        self.stats.start_time = datetime.now()
        self.manifest.record("start", started_at=self.stats.start_time.isoformat())
    
    def set_total(self, total: int):
        """Set total number of files to process.
        
        Args:
            total: Total number of PDFs
        """
        self.stats.total = total
        self.manifest.record("set_total", total=total)
    
    def set_input_output(self, input_dir: str, output_dir: str):
        """Record input and output directories.
        
        Args:
            input_dir: Input directory path
            output_dir: Output directory path
        """
        self.manifest.record("set_input_output", input_dir=input_dir, output_dir=output_dir)
    
    def start_file(self, filename: str):
        """Start processing a file.
        
        Args:
            filename: Name of the file being processed
        """
        self._current_file = filename
        self.manifest.record("start_file", filename=filename)
    
    def complete_file(self, filename: str, success: bool = True):
        """Complete processing a file.
        
        Args:
            filename: Name of the file
            success: Whether processing succeeded (default: True)
        """
        if success:
            self.stats.succeeded += 1
        else:
            self.stats.failed += 1
        self.manifest.record("complete_file", filename=filename, success=success)
    
    def skip_file(self, filename: str):
        """Skip a file (already processed).
        
        Args:
            filename: Name of the file being skipped
        """
        self.stats.skipped += 1
        self.manifest.record("skip_file", filename=filename)
    
    def extracted_image(self, filename: str):
        """Record image extraction.
        
        Args:
            filename: Name of the extracted image
        """
        self.stats.images_extracted += 1
        self.manifest.record("extracted_image", filename=filename)
    
    def extracted_diagram(self, filename: str, model: str):
        """Record diagram extraction.
        
        Args:
            filename: Name of the image containing the diagram
            model: OCR model used for extraction
        """
        self.stats.diagrams_extracted += 1
        self.manifest.record("extracted_diagram", filename=filename, model=model)
    
    def error(self, message: str):
        """Log an error message.
        
        Args:
            message: Error message to display
        """
        self.manifest.record("error", message=message)
    
    def warning(self, message: str):
        """Log a warning message.
        
        Args:
            message: Warning message to display
        """
        self.manifest.record("warning", message=message)
    
    def info(self, message: str):
        """Log an info message.
        
        Args:
            message: Info message to display
        """
        self.manifest.record("info", message=message)
    
    def print_summary(self):
        """Print processing summary."""
        self.manifest.set_summary(
            total=self.stats.total,
            succeeded=self.stats.succeeded,
            failed=self.stats.failed,
            skipped=self.stats.skipped,
            images_extracted=self.stats.images_extracted,
            diagrams_extracted=self.stats.diagrams_extracted,
            duration=self.stats.duration,
            success_rate=round(self.stats.success_rate, 1),
            current_file=self._current_file,
        )
