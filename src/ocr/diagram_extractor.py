"""
Diagram extraction module for Mistral OCR Batch Processor.
"""

import re
from pathlib import Path
from typing import Optional, List

from .client import OCRClient
from src.utils.image_utils import ImageUtils


class DiagramExtractor:
    """Extract diagrams from images as Mermaid or ASCII art.
    
    Attempts to use diagram-specific OCR models first, then validates
    the output to ensure it's actually a diagram (not just text).
    
    Attributes:
        client: OCRClient instance
        DIAGRAM_MODELS: List of models to try for diagram extraction
        MERMAID_PATTERNS: Regex patterns for detecting Mermaid syntax
        ASCII_PATTERNS: Regex patterns for detecting ASCII art
    """
    
    DIAGRAM_MODELS: List[str] = [
        "mistral-ocr-diagram-latest",
        "mistral-diagram-latest",
    ]
    
    # Mermaid syntax patterns for detection
    MERMAID_PATTERNS: List[str] = [
        r'graph\s+(TD|LR|RL|TB)',      # Flowchart direction
        r'classDiagram',
        r'sequenceDiagram',
        r'stateDiagram',
        r'erDiagram',
        r'pie',
        r'gantt',
        r'--->',                      # Arrow connections
        r'-->\s*\|',                 # Arrow with label
        r'\-\-\|',                   # Dashed connections
        r'\=\=',                      # Double line
        r'\[.*\]',                   # Boxes/nodes
        r'class\s+\w+',
        r'\w+\s*\<\|--',
        r'--\>\s*\w+',
    ]
    
    # ASCII art patterns
    ASCII_PATTERNS: List[str] = [
        r'\+--+',                    # Box corners
        r'\+---+',
        r'\+----+',
        r'\|',                       # Vertical lines
        r'\_',                       # Horizontal lines
        r'→',                        # Unicode arrows
        r'↓',
        r'←',
        r'↔',
        r'/\\',                     # Slashes
        r'\\/',
        r'┌', r'┐', r'└', r'┘',        # Box drawing characters
        r'├', r'┤', r'┬', r'┴', r'┼',
    ]
    
    # Common OCR errors to clean up
    OCR_ERROR_PATTERNS: List[tuple] = [
        ('! [', '['),
        ('! ]', ']'),
        ('! -', '-'),
        ('! ->', '->'),
        ('! -->', '-->'),
        ('[ ]', '[]'),
        ('!\n', '\n'),
        ('  !  ', ' '),
    ]
    
    def __init__(self, client: OCRClient):
        """Initialize diagram extractor.
        
        Args:
            client: OCRClient instance for API calls
        """
        self.client = client
    
    def extract(self, image_path: Path) -> Optional[str]:
        """Try to extract diagram as Mermaid/ASCII from image.
        
        Attempts diagram extraction using specialized models, then
        validates the output to ensure it's actually a diagram.
        
        Args:
            image_path: Path to the image file
        
        Returns:
            Extracted diagram in Mermaid/ASCII format, or None if not a diagram
        """
        # First check if image looks like a diagram
        if not ImageUtils.looks_like_diagram(image_path):
            return None
        
        # Try each diagram model
        for model in self.DIAGRAM_MODELS:
            try:
                result = self._try_extract_with_model(image_path, model)
                if result and self._is_valid_diagram(result):
                    cleaned = self._clean_diagram_output(result)
                    return cleaned
            except Exception:
                # Model doesn't exist or failed, try next one
                continue
        
        return None
    
    def extract_from_base64(self, b64_data: str) -> Optional[str]:
        """Extract diagram from base64 encoded image data.
        
        Args:
            b64_data: Base64 encoded image data
        
        Returns:
            Extracted diagram or None
        """
        # Try each diagram model
        for model in self.DIAGRAM_MODELS:
            try:
                result = self.client.process_image(b64_data, model=model)
                if result.pages and len(result.pages) > 0:
                    markdown = result.pages[0].markdown.strip()
                    if markdown and self._is_valid_diagram(markdown):
                        return self._clean_diagram_output(markdown)
            except Exception:
                continue
        
        return None
    
    def _try_extract_with_model(self, image_path: Path, model: str) -> str:
        """Try extraction with a specific model.
        
        Args:
            image_path: Path to image file
            model: OCR model to use
        
        Returns:
            Extracted text from OCR
        """
        # Read and encode the image
        image_data = image_path.read_bytes()
        import base64
        encoded = base64.b64encode(image_data).decode("utf-8")
        
        # Detect format for proper MIME type
        img_format = ImageUtils.detect_format(encoded)
        data_url = f"data:{img_format.mime_type};base64,{encoded}"
        
        # Process with OCR
        result = self.client.process_image(data_url, model=model)
        
        if result.pages and len(result.pages) > 0:
            return result.pages[0].markdown
        
        return ""
    
    def _is_valid_diagram(self, markdown: str) -> bool:
        """Check if result looks like a valid diagram.
        
        Uses heuristics to determine if the OCR output is actually
        a diagram rather than just text.
        
        Args:
            markdown: OCR output text
        
        Returns:
            True if it looks like a diagram, False otherwise
        """
        if not markdown or len(markdown.strip()) < 20:
            return False
        
        markdown_lower = markdown.lower()
        
        # Check for Mermaid syntax
        for pattern in self.MERMAID_PATTERNS:
            if re.search(pattern, markdown, re.IGNORECASE):
                return True
        
        # Check for ASCII art patterns
        for pattern in self.ASCII_PATTERNS:
            if re.search(pattern, markdown):
                return True
        
        # Additional heuristics: diagrams often have specific structures
        # Count occurrences of diagram-like elements
        diagram_elements = 0
        for pattern in self.MERMAID_PATTERNS + self.ASCII_PATTERNS:
            if re.search(pattern, markdown):
                diagram_elements += 1
        
        # If we found multiple diagram-like elements, it's probably a diagram
        if diagram_elements >= 3:
            return True
        
        return False
    
    def _clean_diagram_output(self, markdown: str) -> str:
        """Clean up OCR output for diagrams.
        
        Fixes common OCR errors and removes artifacts.
        
        Args:
            markdown: Raw OCR output
        
        Returns:
            Cleaned diagram text
        """
        # Remove self-referencing image links
        markdown = re.sub(r'!\[.*?\]\(.*?\)', '', markdown)
        
        # Remove standalone special characters on their own lines
        markdown = re.sub(
            r'^\s*[!@#$%^&*()\[\]{}<>+=\|\-/]+\s*$',
            '',
            markdown,
            flags=re.MULTILINE
        )
        
        # Fix common OCR errors in diagrams
        for old, new in self.OCR_ERROR_PATTERNS:
            markdown = markdown.replace(old, new)
        
        # Clean up multiple spaces and empty lines
        markdown = re.sub(r'[ \t]+', ' ', markdown)  # Multiple spaces to single
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)  # Multiple newlines to double
        
        # Remove trailing/leading whitespace
        return markdown.strip()
