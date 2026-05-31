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
    
    Uses a vision model to either convert a diagram into Mermaid or
    describe the image when it is not a diagram.
    
    Attributes:
        client: OCRClient instance
        VISION_MODEL: Multimodal model used for image understanding
        MERMAID_PATTERNS: Regex patterns for detecting Mermaid syntax
        ASCII_PATTERNS: Regex patterns for detecting ASCII art
    """
    
    VISION_MODEL: str = "pixtral-12b-2409"
    VISION_PROMPT: str = (
        "Analyze this image from a document.\n"
        "If it is a diagram, flowchart, UML, or similar structured image, "
        "return valid Mermaid syntax only.\n"
        "If it is not a diagram, return a concise plain-English description.\n"
        "Do not use markdown fences or commentary."
    )
    
    # Mermaid syntax patterns for detection
    MERMAID_PATTERNS: List[str] = [
        r'graph\s+(TD|LR|RL|TB)',      # Flowchart direction
        r'flowchart\s+(TD|LR|RL|TB)', # Flowchart alias
        r'classDiagram',
        r'sequenceDiagram',
        r'stateDiagram',
        r'erDiagram',
        r'pie',
        r'gantt',
        r'--->',                      # Arrow connections
        r'---',                       # Simple arrow/line connections
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
        if not ImageUtils.looks_like_diagram(image_path):
            return None

        result = self._analyze_image_path(image_path)
        if result and self._is_valid_diagram(result):
            return self._clean_diagram_output(result)
        return None
    
    def extract_from_base64(self, b64_data: str) -> Optional[str]:
        """Extract diagram from base64 encoded image data.
        
        Args:
            b64_data: Base64 encoded image data
        
        Returns:
            Extracted diagram or None
        """
        result = self._analyze_base64(b64_data)
        if result and self._is_valid_diagram(result):
            return self._clean_diagram_output(result)
        return None

    def describe(self, image_path: Path) -> Optional[str]:
        """Describe an image or convert it to Mermaid if it is diagram-like."""
        return self._analyze_image_path(image_path)

    def describe_from_base64(self, b64_data: str) -> Optional[str]:
        """Describe an image or convert it to Mermaid if it is diagram-like."""
        return self._analyze_base64(b64_data)

    def is_diagram_text(self, text: str) -> bool:
        """Public helper for checking whether generated text looks like a diagram."""
        return self._is_valid_diagram(text)

    def _analyze_image_path(self, image_path: Path) -> str:
        """Analyze an image file with the vision model.
        
        Args:
            image_path: Path to image file
        
        Returns:
            Mermaid syntax or a concise description
        """
        image_data = image_path.read_bytes()
        import base64
        encoded = base64.b64encode(image_data).decode("utf-8")

        return self._analyze_base64(encoded)

    def _analyze_base64(self, b64_data: str) -> str:
        """Analyze base64 image data with the vision model."""
        try:
            return self.client.describe_image(
                b64_data,
                prompt=self.VISION_PROMPT,
                model=self.VISION_MODEL,
            )
        except Exception:
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
        if not markdown:
            return False

        markdown_stripped = markdown.strip()
        
        # Check for Mermaid syntax
        for pattern in self.MERMAID_PATTERNS:
            if re.search(pattern, markdown, re.IGNORECASE):
                return True
        
        # Check for ASCII art patterns
        for pattern in self.ASCII_PATTERNS:
            if re.search(pattern, markdown):
                return True

        if len(markdown_stripped) < 5:
            return False
        
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
