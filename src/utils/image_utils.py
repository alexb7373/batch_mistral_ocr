"""
Image processing utilities for Mistral OCR Batch Processor.
"""

import base64
from pathlib import Path
from typing import Tuple, Optional
from enum import Enum


class ImageFormat(Enum):
    """Supported image formats with MIME types and extensions."""
    PNG = ("image/png", ".png")
    JPEG = ("image/jpeg", ".jpeg")
    JPG = ("image/jpeg", ".jpg")
    GIF = ("image/gif", ".gif")
    WEBP = ("image/webp", ".webp")
    BMP = ("image/bmp", ".bmp")
    UNKNOWN = ("image/jpeg", ".jpeg")
    
    def __init__(self, mime_type: str, extension: str):
        self.mime_type = mime_type
        self.extension = extension


class ImageUtils:
    """Image processing utilities."""
    
    # Image format signatures (magic bytes)
    FORMAT_SIGNATURES = {
        b'\x89PNG\r\n\x1a\n': ImageFormat.PNG,
        b'\xff\xd8\xff': ImageFormat.JPEG,
        b'\x47\x49\x46\x38': ImageFormat.GIF,
        b'RIFF': ImageFormat.WEBP,
        b'BM': ImageFormat.BMP,
    }
    
    # Extension to format mapping
    EXTENSION_MAP = {
        '.png': ImageFormat.PNG,
        '.jpeg': ImageFormat.JPEG,
        '.jpg': ImageFormat.JPG,
        '.gif': ImageFormat.GIF,
        '.webp': ImageFormat.WEBP,
        '.bmp': ImageFormat.BMP,
    }
    
    @classmethod
    def detect_format(cls, b64_data: str) -> ImageFormat:
        """Detect image format from base64 data.
        
        Args:
            b64_data: Base64 encoded image data (may include data URL header)
        
        Returns:
            ImageFormat enum with mime_type and extension
        """
        # Remove data URL header if present
        if "," in b64_data:
            _, data = b64_data.split(",", 1)
        else:
            data = b64_data
        
        try:
            # Decode just the first 100 bytes to check signature
            raw_data = base64.b64decode(data[:100])
            for signature, img_format in cls.FORMAT_SIGNATURES.items():
                if raw_data.startswith(signature):
                    return img_format
        except Exception:
            pass
        
        # Default to jpeg
        return ImageFormat.JPEG
    
    @classmethod
    def get_mime_type(cls, extension: str) -> str:
        """Get MIME type from file extension.
        
        Args:
            extension: File extension (e.g., '.png', '.jpeg')
        
        Returns:
            MIME type string (e.g., 'image/png')
        """
        ext = extension.lower()
        if ext in cls.EXTENSION_MAP:
            return cls.EXTENSION_MAP[ext].mime_type
        return ImageFormat.JPEG.mime_type
    
    @classmethod
    def get_extension(cls, img_format: ImageFormat) -> str:
        """Get file extension from ImageFormat.
        
        Args:
            img_format: ImageFormat enum
        
        Returns:
            File extension string (e.g., '.png')
        """
        return img_format.extension
    
    @classmethod
    def create_data_url(cls, mime_type: str, b64_data: str) -> str:
        """Create data URL from base64 data.
        
        Args:
            mime_type: MIME type (e.g., 'image/png')
            b64_data: Base64 encoded data (without header)
        
        Returns:
            Data URL string (e.g., 'data:image/png;base64,/9j/4AAQ...')
        """
        return f"data:{mime_type};base64,{b64_data}"
    
    @classmethod
    def decode_base64(cls, b64_data: str) -> bytes:
        """Decode base64 data, handling header if present.
        
        Args:
            b64_data: Base64 encoded data (may include data URL header)
        
        Returns:
            Decoded bytes
        """
        if "," in b64_data:
            _, data = b64_data.split(",", 1)
        else:
            data = b64_data
        return base64.b64decode(data)
    
    @classmethod
    def looks_like_diagram(cls, image_path: Path) -> bool:
        """Heuristic check if image is likely a diagram.
        
        Args:
            image_path: Path to the image file
        
        Returns:
            True if image appears to be a diagram, False otherwise
        """
        # Check file size - diagrams are often larger
        if image_path.stat().st_size > 50 * 1024:  # > 50KB
            return True
        
        # Check aspect ratio (requires Pillow)
        try:
            from PIL import Image
            img = Image.open(image_path)
            width, height = img.size
            aspect_ratio = width / height
            if aspect_ratio > 2.0 or aspect_ratio < 0.5:
                return True
        except ImportError:
            # Pillow not installed, use file size only
            pass
        except Exception:
            # Other image loading errors
            pass
        
        return False
