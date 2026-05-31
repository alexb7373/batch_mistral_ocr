"""
Pytest fixtures for Mistral OCR Batch Processor tests.
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
SRC_PATH = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_PATH))


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def src_path() -> Path:
    """Get the src directory path."""
    return Path(__file__).parent.parent / "src"


@pytest.fixture
def test_data_dir() -> Path:
    """Get the test data directory."""
    return Path(__file__).parent / "data"


# Create mock Mistral client for testing
class MockOCRResponse:
    """Mock OCR response object."""
    
    def __init__(self, pages=None, model="mistral-ocr-latest", usage_info=None):
        self.pages = pages or []
        self.model = model
        self.usage_info = usage_info or MockUsageInfo()


class MockPage:
    """Mock OCR page object."""
    
    def __init__(self, index=0, markdown="", images=None):
        self.index = index
        self.markdown = markdown
        self.images = images or []


class MockImage:
    """Mock OCR image object."""
    
    def __init__(self, image_base64="", img_id=None):
        self.image_base64 = image_base64
        self.id = img_id or "test_img_id"


class MockUsageInfo:
    """Mock usage info object."""
    
    def __init__(self, pages_processed=1, doc_size_bytes=1024):
        self.pages_processed = pages_processed
        self.doc_size_bytes = doc_size_bytes


@pytest.fixture
def mock_ocr_response():
    """Create a mock OCR response."""
    page = MockPage(
        index=0,
        markdown="# Test Document\n\nThis is a test.",
        images=[MockImage(image_base64="data:image/png;base64,testdata")]
    )
    return MockOCRResponse(
        pages=[page],
        model="mistral-ocr-latest",
        usage_info=MockUsageInfo(pages_processed=1, doc_size_bytes=1024)
    )


@pytest.fixture
def mock_client(mocker):
    """Create a mock Mistral OCR client."""
    from src.ocr.client import OCRClient
    
    # Create a mock client that doesn't make actual API calls
    mock = mocker.MagicMock(spec=OCRClient)
    mock.process_document.return_value = MockOCRResponse()
    mock.process_image.return_value = MockOCRResponse()
    mock.upload_file.return_value = "https://mock-url.com"
    
    return mock
