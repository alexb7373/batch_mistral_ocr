"""
Tests for usage tracking module.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import json
import time

from src.utils.usage_tracker import UsageTracker, UsageStats, UsageInfo, MISTRAL_OCR_PRICING


class TestUsageInfo:
    """Tests for UsageInfo dataclass."""
    
    def test_default_values(self):
        """Test default UsageInfo values."""
        info = UsageInfo()
        assert info.pages_processed == 0
        assert info.doc_size_bytes == 0
        assert info.model == ""
    
    def test_estimated_cost_with_known_model(self):
        """Test cost estimation with known model."""
        info = UsageInfo(pages_processed=10, model="mistral-ocr-latest")
        expected_cost = 10 * MISTRAL_OCR_PRICING["mistral-ocr-latest"]["price_per_page_usd"]
        assert info.estimated_cost_usd == pytest.approx(expected_cost)

    def test_estimated_cost_with_annotated_pages(self):
        """Test cost estimation includes annotated pages."""
        info = UsageInfo(
            pages_processed=10,
            annotated_pages_processed=2,
            model="mistral-ocr-latest",
        )
        expected_cost = (
            10 * MISTRAL_OCR_PRICING["mistral-ocr-latest"]["price_per_page_usd"]
            + 2 * MISTRAL_OCR_PRICING["mistral-ocr-latest"]["price_per_annotated_page_usd"]
        )
        assert info.estimated_cost_usd == pytest.approx(expected_cost)
    
    def test_estimated_cost_with_unknown_model(self):
        """Test cost estimation with unknown model uses default."""
        info = UsageInfo(pages_processed=5, model="unknown-model")
        expected_cost = 5 * MISTRAL_OCR_PRICING["default"]["price_per_page_usd"]
        assert info.estimated_cost_usd == pytest.approx(expected_cost)


class TestUsageStats:
    """Tests for UsageStats dataclass."""
    
    def test_default_values(self):
        """Test default UsageStats values."""
        stats = UsageStats()
        assert stats.total_pages_processed == 0
        assert stats.total_images_processed == 0
        assert stats.total_document_api_calls == 0
        assert stats.total_image_api_calls == 0
        assert stats.total_api_calls == 0
        assert stats.estimated_cost_usd == 0.0
    
    def test_add_usage(self):
        """Test adding usage information."""
        stats = UsageStats()
        usage_info = UsageInfo(
            pages_processed=5,
            annotated_pages_processed=2,
            doc_size_bytes=1000,
            model="mistral-ocr-latest",
        )
        stats.add_usage(usage_info)
        
        assert stats.total_pages_processed == 5
        assert stats.total_annotated_pages_processed == 2
        assert stats.total_bytes_processed == 1000
        assert stats.total_document_api_calls == 1
        assert stats.total_api_calls == 1
        assert stats.models_used["mistral-ocr-latest"] == 1
    
    def test_add_image_usage(self):
        """Test adding image usage."""
        stats = UsageStats()
        stats.add_image_usage("mistral-ocr-latest")
        
        assert stats.total_images_processed == 1
        assert stats.total_image_api_calls == 1
        assert stats.total_api_calls == 1
        assert stats.models_used["mistral-ocr-latest"] == 1
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        import time
        from datetime import datetime, timedelta
        
        stats = UsageStats()
        stats.start_time = datetime.now()
        time.sleep(0.1)
        stats.end_time = datetime.now()
        
        assert stats.duration_seconds >= 0.1
        assert stats.duration_seconds < 1.0
    
    def test_pages_per_second(self):
        """Test pages per second calculation."""
        stats = UsageStats()
        stats.total_pages_processed = 10
        stats.start_time = datetime(2024, 1, 1, 12, 0, 0)
        stats.end_time = datetime(2024, 1, 1, 12, 0, 5)  # 5 seconds
        
        assert stats.pages_per_second == pytest.approx(2.0)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = UsageStats(
            total_pages_processed=5,
            total_annotated_pages_processed=2,
            total_images_processed=3,
            total_bytes_processed=1000,
            total_api_calls=8,
            estimated_cost_usd=0.004
        )
        stats.start_time = datetime(2024, 1, 1, 12, 0, 0)
        stats.end_time = datetime(2024, 1, 1, 12, 0, 1)
        
        result = stats.to_dict()
        
        assert result["document_pages_processed"] == 5
        assert result["document_annotated_pages_processed"] == 2
        assert result["document_api_calls"] == 0
        assert result["image_api_calls"] == 0
        assert result["total_api_calls"] == 8
        assert result["total_images_processed"] == 3
        assert result["total_bytes_processed"] == 1000
        assert "total_pages_processed" not in result
        assert "total_annotated_pages_processed" not in result
        assert "total_document_api_calls" not in result
        assert "total_image_api_calls" not in result
        assert "start_time" in result
        assert "end_time" in result
    
    def test_save_to_file(self):
        """Test saving to file."""
        stats = UsageStats(total_pages_processed=5, estimated_cost_usd=0.005)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "usage.json"
            stats.save_to_file(output_path)
            
            assert output_path.exists()
            with open(output_path) as f:
                data = json.load(f)
            
        assert data["document_pages_processed"] == 5
        assert "total_pages_processed" not in data
        assert data["estimated_cost_usd"] == pytest.approx(0.005)


class TestUsageTracker:
    """Tests for UsageTracker class."""
    
    def test_start_and_end(self):
        """Test start and end methods."""
        tracker = UsageTracker()
        tracker.start()
        
        assert tracker.stats.start_time is not None
        
        tracker.end()
        assert tracker.stats.end_time is not None
    
    def test_extract_usage_info(self):
        """Test extracting usage info from response."""
        tracker = UsageTracker()
        
        # Create a mock response
        class MockUsageInfo:
            pages_processed = 3
            doc_size_bytes = 2048
        
        class MockResponse:
            usage_info = MockUsageInfo()
            model = "mistral-ocr-latest"
        
        response = MockResponse()
        usage_info = tracker.extract_usage_info(response)
        
        assert usage_info.pages_processed == 3
        assert usage_info.doc_size_bytes == 2048
        assert usage_info.model == "mistral-ocr-latest"
    
    def test_extract_usage_info_missing(self):
        """Test extracting usage info when missing."""
        tracker = UsageTracker()
        
        class MockResponse:
            pass
        
        response = MockResponse()
        usage_info = tracker.extract_usage_info(response)
        
        assert usage_info.pages_processed == 0
        assert usage_info.doc_size_bytes == 0
    
    def test_record_document_ocr(self):
        """Test recording document OCR."""
        tracker = UsageTracker()
        
        class MockUsageInfo:
            pages_processed = 2
            annotated_pages_processed = 1
            doc_size_bytes = 1024
        
        class MockResponse:
            usage_info = MockUsageInfo()
            model = "mistral-ocr-latest"
        
        tracker.record_document_ocr(MockResponse(), "mistral-ocr-latest")
        
        assert tracker.stats.total_pages_processed == 2
        assert tracker.stats.total_annotated_pages_processed == 1
        assert tracker.stats.total_document_api_calls == 1
        assert tracker.stats.total_api_calls == 1

    def test_record_image_ocr_with_response(self):
        """Test recording image OCR from an API response."""
        tracker = UsageTracker()

        class MockUsageInfo:
            pages_processed = 1
            annotated_pages_processed = 0
            doc_size_bytes = 512

        class MockPage:
            markdown = "graph TD\n  A --> B"

        class MockResponse:
            usage_info = MockUsageInfo()
            pages = [MockPage()]
            model = "mistral-ocr-latest"

        tracker.record_image_ocr(MockResponse(), "mistral-ocr-latest")

        assert tracker.stats.total_pages_processed == 1
        assert tracker.stats.total_annotated_pages_processed == 0
        assert tracker.stats.total_images_processed == 0
        assert tracker.stats.total_document_api_calls == 1
        assert tracker.stats.total_image_api_calls == 0
        assert tracker.stats.total_api_calls == 1
        assert tracker.stats.models_used["mistral-ocr-latest"] == 1
    
    def test_record_image_ocr(self):
        """Test recording image OCR."""
        tracker = UsageTracker()
        tracker.record_image_ocr("mistral-ocr-diagram-latest")
        
        assert tracker.stats.total_images_processed == 1
        assert tracker.stats.total_image_api_calls == 1
        assert tracker.stats.total_api_calls == 1
        assert tracker.stats.models_used["mistral-ocr-diagram-latest"] == 1
    
    def test_get_stats(self):
        """Test getting stats."""
        tracker = UsageTracker()
        stats = tracker.get_stats()
        
        assert isinstance(stats, UsageStats)
    
    def test_print_summary(self, capsys):
        """Test printing summary."""
        tracker = UsageTracker()
        tracker.stats.total_pages_processed = 10
        tracker.stats.total_api_calls = 5
        tracker.stats.total_document_api_calls = 3
        tracker.stats.total_image_api_calls = 2
        tracker.stats.estimated_cost_usd = 0.005
        
        tracker.print_summary()
        
        captured = capsys.readouterr()
        assert "API Usage Summary" in captured.out
        assert "10" in captured.out  # pages processed
        assert "Document calls" in captured.out
        assert "5" in captured.out  # API calls
