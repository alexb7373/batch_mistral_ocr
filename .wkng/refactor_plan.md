# Refactoring Plan for batch_mistral_ocr

> **Status:** Proposed  
> **Date:** 2026-05-31  
> **Author:** Mistral Vibe (based on OCR output analysis)  
> **Objective:** Improve code architecture using SOLID principles, particularly Single Responsibility  

---

## 🎯 Motivation

### Issues Identified from OCR Output Analysis

1. **Diagram OCR Quality**: Images containing diagrams (e.g., Observer pattern UML) return poor text like `! ! ! ! subject` instead of structured Mermaid/ASCII format
2. **Monolithic Script**: `ocr_batch.py` (~280+ lines) handles configuration, API clients, file I/O, image processing, OCR, and progress tracking
3. **No Separation of Concerns**: Violates Single Responsibility Principle
4. **Difficult to Test**: No module boundaries, hard to mock dependencies
5. **Hard to Extend**: Adding features requires modifying the single file

### OCR Output Examples

From `output_books/An Introduction to Design Patterns.md`:
```markdown
**OCR Extracted Text from image:**
page003_image0.jpeg
# observers

!
!
!
!
subject
```

This is a UML diagram that should ideally be converted to Mermaid format.

---

## 🏗️ Proposed Modular Architecture

### Directory Structure

```
batch_mistral_ocr/
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Configuration loading & validation
│   ├── ocr/
│   │   ├── __init__.py
│   │   ├── client.py             # Mistral API client wrapper
│   │   ├── processors.py         # PDF & image processors
│   │   └── diagram_extractor.py  # Diagram-specific extraction logic
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_utils.py         # File I/O helpers
│   │   ├── image_utils.py        # Image format detection & processing
│   │   └── logging.py            # Progress tracking & logging
│   └── models/
│       ├── __init__.py
│       └── types.py              # Type definitions (dataclasses)
├── config.py                    # Local config (gitignored)
├── ocr_batch.py                 # Thin CLI entry point
├── requirements.txt
├── AGENTS.md
└── .wkng/
    └── refactor_plan.md          # This file
```

---

## 📦 Module Breakdown

### 1. `src/config/settings.py` - Configuration Module

**Responsibility:** Load and validate all configuration  
**Single Responsibility:** Configuration management only

```python
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class AppConfig:
    """Application configuration."""
    input_dir: Path
    output_dir: Path
    api_key: str
    diagram_models: list[str]
    regular_model: str
    force_reprocess: bool = False
    max_retries: int = 3

def load_config() -> AppConfig:
    """Load configuration from multiple sources with fallback.
    
    Priority order:
    1. Command-line arguments
    2. config/config.py
    3. Environment variables
    4. Default values
    """
    pass
```

### 2. `src/ocr/client.py` - API Client Wrapper

**Responsibility:** All Mistral API interactions  
**Single Responsibility:** API communication only

```python
from mistralai.client import Mistral
from mistralai.client.models import DocumentURLChunk, ImageURLChunk
from typing import Optional
import time

class OCRClient:
    """Wrapper for Mistral OCR API with retry logic."""
    
    def __init__(self, api_key: str, max_retries: int = 3):
        self.client = Mistral(api_key=api_key)
        self.max_retries = max_retries
    
    def process_document(
        self, 
        document_url: str, 
        model: str = "mistral-ocr-latest",
        include_image_base64: bool = True
    ):
        """Process a document with OCR."""
    
    def process_image(self, image_url: str, model: str = None):
        """Process an image with OCR."""
    
    def upload_file(self, file_path: Path, purpose: str = "ocr") -> str:
        """Upload a file and return signed URL."""
        pass
    
    def _retry_on_failure(self, func, *args, **kwargs):
        """Retry a function call on failure."""
        pass
```

### 3. `src/ocr/processors.py` - Processing Logic

**Responsibility:** Process PDFs and images  
**Single Responsibility:** Document/image processing only

```python
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .client import OCRClient
from ..config.settings import AppConfig
from ..utils import file_utils, image_utils
from ..ocr.diagram_extractor import DiagramExtractor

@dataclass
class ProcessResult:
    """Result of processing a PDF."""
    success: bool
    output_path: Optional[Path]
    error: Optional[str]
    images_processed: int = 0
    pages_processed: int = 0

class PDFProcessor:
    """Process PDF documents through OCR."""
    
    def __init__(self, client: OCRClient, config: AppConfig):
        self.client = client
        self.config = config
        self.image_processor = ImageProcessor(client)
    
    def process(self, pdf_path: Path) -> ProcessResult:
        """Process a single PDF file."""
        pass
    
    def _should_skip(self, pdf_path: Path) -> bool:
        """Check if PDF should be skipped."""
        pass

class ImageProcessor:
    """Process individual images from PDF pages."""
    
    def __init__(self, client: OCRClient):
        self.client = client
        self.diagram_extractor = DiagramExtractor(client)
    
    def process(self, image_path: Path) -> str:
        """Process an image and return extracted text.
        
        Attempts diagram extraction first, then falls back to regular OCR.
        """
        pass
    
    def save_image(self, b64_data: str, output_path: Path) -> Path:
        """Save base64 image data to disk."""
        pass
```

### 4. `src/ocr/diagram_extractor.py` - Diagram Specialist

**Responsibility:** Extract and convert diagrams from images  
**Single Responsibility:** Diagram detection and conversion only

```python
import re
from pathlib import Path
from typing import Optional

from .client import OCRClient

class DiagramExtractor:
    """Extract diagrams from images as Mermaid or ASCII art."""
    
    DIAGRAM_MODELS = [
        "mistral-ocr-diagram-latest",
        "mistral-diagram-latest",
    ]
    
    # Mermaid syntax patterns for detection
    MERMAID_PATTERNS = [
        r'graph\s+(TD|LR|RL|TB)',      # Flowchart
        r'classDiagram',
        r'sequenceDiagram',
        r'stateDiagram',
        r'erDiagram',
        r'-->', r'-->', r'==>',          # Arrows/connections
        r'\[.*\]',                     # Boxes/nodes
    ]
    
    # ASCII art patterns
    ASCII_PATTERNS = [
        r'\+--+', r'\+--+\+',         # Box drawing
        r'\|', r'\_',                  # Vertical/horizontal lines
        r'→', r'↓', r'←', r'↔',         # Unicode arrows
        r'/\\', r'\\/',              # Slashes
    ]
    
    def __init__(self, client: OCRClient):
        self.client = client
    
    def extract(self, image_path: Path) -> Optional[str]:
        """Try to extract diagram as Mermaid/ASCII from image.
        
        Returns:
            str: Extracted diagram in Mermaid/ASCII format, or None if not a diagram
        """
        # First check if image looks like a diagram
        if not self._looks_like_diagram(image_path):
            return None
        
        # Try each diagram model
        for model in self.DIAGRAM_MODELS:
            try:
                result = self._try_extract_with_model(image_path, model)
                if result and self._is_valid_diagram(result):
                    return self._clean_diagram_output(result)
            except Exception:
                continue
        
        return None
    
    def _looks_like_diagram(self, image_path: Path) -> bool:
        """Heuristic check if image is likely a diagram."""
        # Check file size - diagrams are often larger
        if image_path.stat().st_size > 50 * 1024:  # > 50KB
            return True
        
        # Check aspect ratio
        try:
            from PIL import Image
            img = Image.open(image_path)
            width, height = img.size
            aspect_ratio = width / height
            if aspect_ratio > 2.0 or aspect_ratio < 0.5:
                return True
        except ImportError:
            pass
        
        return False
    
    def _try_extract_with_model(self, image_path: Path, model: str) -> str:
        """Try extraction with a specific model."""
        pass
    
    def _is_valid_diagram(self, markdown: str) -> bool:
        """Check if result looks like a valid diagram."""
        if not markdown or len(markdown.strip()) < 20:
            return False
        
        # Check for Mermaid syntax
        for pattern in self.MERMAID_PATTERNS:
            if re.search(pattern, markdown, re.IGNORECASE):
                return True
        
        # Check for ASCII art
        for pattern in self.ASCII_PATTERNS:
            if re.search(pattern, markdown):
                return True
        
        return False
    
    def _clean_diagram_output(self, markdown: str) -> str:
        """Clean up OCR output for diagrams."""
        # Remove self-referencing image links
        markdown = re.sub(r'!\[.*?\]\(.*?\)', '', markdown)
        
        # Remove standalone special characters
        markdown = re.sub(r'^\s*[!@#$%^&*()\[\]{}]+\s*$', '', markdown, flags=re.MULTILINE)
        
        # Fix common OCR errors in diagrams
        replacements = {
            '! [': '[',
            '! ]': ']',
            '! -': '-',
            '! ->': '->',
            '! -->': '-->',
            '[ ]': '[]',
        }
        for old, new in replacements.items():
            markdown = markdown.replace(old, new)
        
        return markdown.strip()
```

### 5. `src/utils/file_utils.py` - File Utilities

**Responsibility:** File system operations  
**Single Responsibility:** File I/O only

```python
from pathlib import Path
from typing import Optional
import base64

class FileUtils:
    """File system utilities."""
    
    @staticmethod
    def ensure_directory(path: Path) -> None:
        """Ensure directory exists, create if not."""
        path.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def save_image(data: bytes, path: Path) -> None:
        """Save binary image data to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    
    @staticmethod
    def read_file(path: Path) -> bytes:
        """Read file as bytes."""
        return path.read_bytes()
    
    @staticmethod
    def write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
    
    @staticmethod
    def decode_base64(b64_data: str) -> bytes:
        """Decode base64 data, handling header if present."""
        if "," in b64_data:
            _, data = b64_data.split(",", 1)
        else:
            data = b64_data
        return base64.b64decode(data)
```

### 6. `src/utils/image_utils.py` - Image Utilities

**Responsibility:** Image format detection and processing  
**Single Responsibility:** Image-specific operations only

```python
import base64
from pathlib import Path
from typing import Tuple

class ImageUtils:
    """Image processing utilities."""
    
    # Image format signatures (magic bytes)
    FORMAT_SIGNATURES = {
        b'\x89PNG\r\n\x1a\n': ('image/png', '.png'),
        b'\xff\xd8\xff': ('image/jpeg', '.jpeg'),
        b'\x47\x49\x46\x38': ('image/gif', '.gif'),
        b'RIFF': ('image/webp', '.webp'),
        b'BM': ('image/bmp', '.bmp'),
    }
    
    @staticmethod
    def detect_format(b64_data: str) -> Tuple[str, str]:
        """Detect image format from base64 data.
        
        Returns:
            tuple: (mime_type, file_extension)
        """
        try:
            # Decode just the first 100 bytes to check signature
            raw_data = base64.b64decode(b64_data[:100])
            for signature, (mime, ext) in ImageUtils.FORMAT_SIGNATURES.items():
                if raw_data.startswith(signature):
                    return mime, ext
        except Exception:
            pass
        
        # Default to jpeg
        return 'image/jpeg', '.jpeg'
    
    @staticmethod
    def get_mime_type(extension: str) -> str:
        """Get MIME type from file extension."""
        ext_map = {
            '.png': 'image/png',
            '.jpeg': 'image/jpeg',
            '.jpg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
        }
        return ext_map.get(extension.lower(), 'image/jpeg')
    
    @staticmethod
    def create_data_url(mime_type: str, b64_data: str) -> str:
        """Create data URL from base64 data."""
        return f"data:{mime_type};base64,{b64_data}"
```

### 7. `src/utils/logging.py` - Progress Tracking

**Responsibility:** Logging and progress reporting  
**Single Responsibility:** Progress tracking only

```python
import sys
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ProcessingStats:
    """Processing statistics."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    images_extracted: int = 0
    diagrams_extracted: int = 0
    start_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total == 0:
            return 0.0
        return (self.succeeded / self.total) * 100
    
    @property
    def duration(self) -> str:
        """Calculate duration."""
        if not self.start_time:
            return "0:00:00"
        duration = datetime.now() - self.start_time
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{duration.days}d {hours}:{minutes:02d}:{seconds:02d}"

class ProgressTracker:
    """Track and report processing progress."""
    
    def __init__(self, verbose: bool = True):
        self.stats = ProcessingStats()
        self.verbose = verbose
        self._current_file: Optional[str] = None
    
    def start(self):
        """Start processing."""
        self.stats.start_time = datetime.now()
        if self.verbose:
            print("=" * 60)
            print("🚀 Mistral OCR Batch Processor")
            print("=" * 60)
    
    def set_total(self, total: int):
        """Set total number of files to process."""
        self.stats.total = total
        if self.verbose:
            print(f"📚 Found {total} PDF(s) to process\n")
    
    def start_file(self, filename: str):
        """Start processing a file."""
        self._current_file = filename
        if self.verbose:
            print(f"🔍 Processing {filename}")
    
    def complete_file(self, filename: str, success: bool = True):
        """Complete processing a file."""
        if success:
            self.stats.succeeded += 1
            if self.verbose:
                print(f"✅ Saved: {filename}")
        else:
            self.stats.failed += 1
    
    def skip_file(self, filename: str):
        """Skip a file."""
        self.stats.skipped += 1
        if self.verbose:
            print(f"⏭️  Skipping {filename}, already processed.")
    
    def extracted_image(self, filename: str):
        """Record image extraction."""
        self.stats.images_extracted += 1
        if self.verbose:
            print(f"  🖼️  Saved image: {filename}")
    
    def extracted_diagram(self, filename: str, model: str):
        """Record diagram extraction."""
        self.stats.diagrams_extracted += 1
        if self.verbose:
            print(f"  📊 Extracted diagram from {filename} using {model}")
    
    def error(self, message: str):
        """Log an error."""
        if self.verbose:
            print(f"❌ {message}")
    
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
```

### 8. `src/models/types.py` - Type Definitions

**Responsibility:** Shared type definitions  
**Single Responsibility:** Type definitions only

```python
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

class ImageFormat(Enum):
    """Supported image formats."""
    PNG = ("image/png", ".png")
    JPEG = ("image/jpeg", ".jpeg")
    GIF = ("image/gif", ".gif")
    WEBP = ("image/webp", ".webp")
    BMP = ("image/bmp", ".bmp")
    UNKNOWN = ("image/jpeg", ".jpeg")
    
    def __init__(self, mime_type: str, extension: str):
        self.mime_type = mime_type
        self.extension = extension

@dataclass
class OCRPage:
    """Represents an OCR-processed page."""
    index: int
    markdown: str
    images: List["OCRImage"] = None
    
    def __post_init__(self):
        if self.images is None:
            self.images = []

@dataclass
class OCRImage:
    """Represents an image extracted from a PDF page."""
    index: int
    image_base64: str
    id: Optional[str] = None
    format: Optional[ImageFormat] = None

@dataclass
class OCRResult:
    """Result of OCR processing."""
    pages: List[OCRPage]
    total_pages: int
    model: str
```

### 9. `ocr_batch.py` - Thin CLI Entry Point

**Responsibility:** Command-line interface only  
**Single Responsibility:** CLI and orchestration only

```python
#!/usr/bin/env python3
"""
Batch OCR processor for PDF documents using Mistral OCR API.
"""

import sys
from pathlib import Path

# Add src to path
SRC_PATH = Path(__file__).parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from config.settings import load_config, AppConfig
from ocr.client import OCRClient
from ocr.processors import PDFProcessor
from utils.logging import ProgressTracker


def main():
    """Main entry point."""
    try:
        # Load configuration
        config = load_config()
        
        # Initialize tracker
        tracker = ProgressTracker()
        tracker.start()
        
        # Initialize client
        client = OCRClient(config.api_key, max_retries=config.max_retries)
        
        # Initialize processor
        processor = PDFProcessor(client, config)
        
        # Find PDFs
        pdf_files = list(config.input_dir.glob("*.pdf"))
        tracker.set_total(len(pdf_files))
        
        if not pdf_files:
            tracker.error("No PDF files found in input directory.")
            return
        
        # Process each PDF
        for pdf_file in sorted(pdf_files):
            tracker.start_file(pdf_file.name)
            
            if processor.should_skip(pdf_file):
                tracker.skip_file(pdf_file.name)
                continue
            
            result = processor.process(pdf_file)
            tracker.complete_file(pdf_file.name, result.success)
            
            if not result.success and result.error:
                tracker.error(f"{pdf_file.name}: {result.error}")
        
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
```

---

## 🚀 Implementation Roadmap

### Phase 1: Basic Refactoring (1-2 hours)
**Objective:** Establish module structure and move existing code

- [ ] Create `src/` directory structure with `__init__.py` files
- [ ] Move `load_config()` → `src/config/settings.py`
- [ ] Move image format detection → `src/utils/image_utils.py`
- [ ] Move file operations → `src/utils/file_utils.py`
- [ ] Create `src/models/types.py` with dataclasses
- [ ] Update `ocr_batch.py` imports to use `src` modules
- [ ] Verify existing functionality still works

### Phase 2: OCR Client Abstraction (1 hour)
**Objective:** Isolate Mistral API interactions

- [ ] Create `src/ocr/client.py` with `OCRClient` class
- [ ] Move all Mistral API calls to this class
- [ ] Add retry logic with exponential backoff
- [ ] Add error handling for rate limits
- [ ] Update existing code to use `OCRClient`

### Phase 3: Processing Modules (2 hours)
**Objective:** Extract processing logic into dedicated modules

- [ ] Create `src/ocr/processors.py` with `PDFProcessor` and `ImageProcessor`
- [ ] Move PDF processing logic from main script
- [ ] Move image processing logic from main script
- [ ] Add proper type hints
- [ ] Add input validation

### Phase 4: Diagram Extraction (1-2 hours)
**Objective:** Add intelligent diagram extraction

- [ ] Create `src/ocr/diagram_extractor.py` with `DiagramExtractor` class
- [ ] Implement diagram detection heuristics
- [ ] Add Mermaid syntax validation
- [ ] Add ASCII art cleanup
- [ ] Add diagram-specific OCR model support
- [ ] Test with actual diagram images

### Phase 5: Logging & Tracking (1 hour)
**Objective:** Professional progress tracking

- [ ] Create `src/utils/logging.py` with `ProgressTracker` class
- [ ] Replace all print statements with tracker methods
- [ ] Add timing information
- [ ] Add statistics collection
- [ ] Add verbose/quiet mode support

---

## 📊 Benefits Comparison

| Aspect | Current | Proposed |
|--------|---------|----------|
| **Lines of Code** | ~280 (1 file) | ~400-500 (8-10 files) |
| **Testability** | ❌ Hard to test | ✅ Easy to mock and test |
| **Extensibility** | ❌ Modify one file | ✅ Add modules without touching existing |
| **Maintainability** | ❌ Monolithic | ✅ Modular, clear boundaries |
| **Error Isolation** | ❌ One error breaks all | ✅ Errors contained in modules |
| **Reusability** | ❌ PDF-specific | ✅ Modules reusable for other tasks |
| **Collaboration** | ❌ Single file conflict | ✅ Multiple devs can work |
| **Diagram Support** | ⚠️ Basic OCR | ✅ Smart diagram detection |
| **Type Safety** | ⚠️ Partial | ✅ Full type hints |

---

## 💡 Additional Recommendations

### 1. Add pytest Support
Create test structure:
```
tests/
├── __init__.py
├── conftest.py          # Fixtures
├── test_config.py
├── test_ocr_client.py
├── test_processors.py
└── test_diagram_extractor.py
```

### 2. Add CLI Arguments
Support command-line configuration:
```python
import argparse

parser = argparse.ArgumentParser(description="Batch OCR Processor")
parser.add_argument("--input", "-i", help="Input directory", default=None)
parser.add_argument("--output", "-o", help="Output directory", default=None)
parser.add_argument("--force", "-f", action="store_true", help="Force reprocessing")
parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")
```

### 3. Add Rate Limiting
Prevent API rate limit issues:
```python
import time
from functools import wraps

def rate_limit(max_calls: int, period: int):
    """Rate limit decorator."""
    def decorator(func):
        calls = []
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            calls[:] = [c for c in calls if now - c < period]
            if len(calls) >= max_calls:
                sleep_time = period - (now - calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                calls[:] = [c for c in calls if now - c < period]
            calls.append(time.time())
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

### 4. Add Environment Variable Configuration
Support customization via environment:
```python
DIAGRAM_MODEL = os.getenv("MISTRAL_DIAGRAM_MODEL", "mistral-ocr-diagram-latest")
REGULAR_MODEL = os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")
MAX_RETRIES = int(os.getenv("MISTRAL_MAX_RETRIES", "3"))
RATE_LIMIT = int(os.getenv("MISTRAL_RATE_LIMIT_CALLS", "10"))
RATE_LIMIT_PERIOD = int(os.getenv("MISTRAL_RATE_LIMIT_PERIOD", "60"))
```

### 5. Add Dependencies
Update `requirements.txt`:
```
# Core dependencies
mistralai>=1.0.0
python-dotenv>=1.0.0

# Optional: for image analysis
Pillow>=10.0.0

# Development dependencies (in requirements-dev.txt)
pytest>=7.0.0
pytest-mock>=3.0.0
black>=24.0.0
mypy>=1.0.0
```

---

## 📝 File Checklist

- [ ] `src/__init__.py`
- [ ] `src/config/__init__.py`
- [ ] `src/config/settings.py`
- [ ] `src/ocr/__init__.py`
- [ ] `src/ocr/client.py`
- [ ] `src/ocr/processors.py`
- [ ] `src/ocr/diagram_extractor.py`
- [ ] `src/utils/__init__.py`
- [ ] `src/utils/file_utils.py`
- [ ] `src/utils/image_utils.py`
- [ ] `src/utils/logging.py`
- [ ] `src/models/__init__.py`
- [ ] `src/models/types.py`
- [ ] Update `ocr_batch.py` (thin CLI)
- [ ] Update `requirements.txt`
- [ ] Create `requirements-dev.txt`
- [ ] Create `tests/` directory

---

## 🎯 Success Criteria

- [ ] All existing tests pass (if any)
- [ ] OCR output quality same or better
- [ ] Diagram extraction works for UML diagrams
- [ ] Code is properly type-hinted
- [ ] Each module has single responsibility
- [ ] Easy to add new features
- [ ] Easy to test individual components

---

## 📚 References

- SOLID Principles: https://en.wikipedia.org/wiki/SOLID
- Single Responsibility Principle: https://en.wikipedia.org/wiki/Single-responsibility_principle
- Mistral OCR Documentation: https://docs.mistral.ai/capabilities/OCR/basic_ocr/
- Mistral Diagram OCR: (check latest documentation)

---

**Status:** Ready for implementation  
**Priority:** High (current monolithic code is hard to maintain)  
**Estimated Effort:** 8-10 hours total  
**Risk:** Low (can be done incrementally)
