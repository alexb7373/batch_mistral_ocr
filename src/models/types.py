"""
Type definitions for Mistral OCR Batch Processor.
"""

from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class OCRImage:
    """Represents an image extracted from a PDF page."""
    index: int
    image_base64: str
    id: Optional[str] = None
    format: Optional[str] = None


@dataclass
class OCRPage:
    """Represents an OCR-processed page."""
    index: int
    markdown: str
    images: List[OCRImage] = field(default_factory=list)


@dataclass
class OCRResult:
    """Result of OCR processing for a document."""
    pages: List[OCRPage]
    total_pages: int
    model: str


@dataclass
class ProcessResult:
    """Result of processing a single PDF file."""
    success: bool
    output_path: Optional[Path] = None
    error: Optional[str] = None
    images_processed: int = 0
    pages_processed: int = 0
    diagrams_extracted: int = 0
    skipped: bool = False
