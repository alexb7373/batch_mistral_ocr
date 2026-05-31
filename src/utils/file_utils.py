"""
File system utilities for Mistral OCR Batch Processor.
"""

import base64
from pathlib import Path
from typing import Optional


class FileUtils:
    """File system utilities."""
    
    @staticmethod
    def ensure_directory(path: Path) -> None:
        """Ensure directory exists, create if not.
        
        Args:
            path: Directory path
        """
        path.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def save_image(data: bytes, path: Path) -> None:
        """Save binary image data to file.
        
        Args:
            data: Binary image data
            path: Output file path
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    
    @staticmethod
    def read_file(path: Path) -> bytes:
        """Read file as bytes.
        
        Args:
            path: File path
        
        Returns:
            File contents as bytes
        """
        return path.read_bytes()
    
    @staticmethod
    def write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
        """Write text to file.
        
        Args:
            path: Output file path
            content: Text content to write
            encoding: Text encoding (default: utf-8)
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
    
    @staticmethod
    def append_text(path: Path, content: str, encoding: str = "utf-8") -> None:
        """Append text to file.
        
        Args:
            path: File path
            content: Text content to append
            encoding: Text encoding (default: utf-8)
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding, append=True)
    
    @staticmethod
    def decode_base64(b64_data: str) -> bytes:
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
    
    @staticmethod
    def file_exists(path: Path) -> bool:
        """Check if file exists.
        
        Args:
            path: File path
        
        Returns:
            True if file exists, False otherwise
        """
        return path.exists() and path.is_file()
    
    @staticmethod
    def get_file_size(path: Path) -> int:
        """Get file size in bytes.
        
        Args:
            path: File path
        
        Returns:
            File size in bytes
        """
        return path.stat().st_size
    
    @staticmethod
    def list_pdfs(directory: Path) -> list[Path]:
        """List all PDF files in a directory.
        
        Args:
            directory: Directory to search
        
        Returns:
            List of Path objects for PDF files
        """
        return list(directory.glob("*.pdf"))
    
    @staticmethod
    def get_unique_output_path(input_path: Path, output_dir: Path, extension: str = ".md") -> Path:
        """Generate unique output path based on input path.
        
        Args:
            input_path: Input file path
            output_dir: Output directory
            extension: Output file extension
        
        Returns:
            Output file path
        """
        # Use input file stem as output filename
        output_name = input_path.stem + extension
        return output_dir / output_name
