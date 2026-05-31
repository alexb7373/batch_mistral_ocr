"""
API usage tracking and accounting for Mistral OCR Batch Processor.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


# Mistral OCR pricing.
# Mistral bills OCR per page, with a separate annotation rate.
MISTRAL_OCR_PRICING = {
    "mistral-ocr-2512": {
        "price_per_page_usd": 0.002,  # $2 / 1000 pages
        "price_per_annotated_page_usd": 0.003,  # $3 / 1000 annotated pages
    },
    "mistral-ocr-latest": {
        "price_per_page_usd": 0.002,
        "price_per_annotated_page_usd": 0.003,
    },
    # Default pricing for unknown models
    "default": {
        "price_per_page_usd": 0.002,
        "price_per_annotated_page_usd": 0.003,
    },
}

@dataclass
class UsageInfo:
    """Usage information from a single OCR API call."""
    pages_processed: int = 0
    annotated_pages_processed: int = 0
    doc_size_bytes: int = 0
    model: str = ""
    
    @property
    def estimated_cost_usd(self) -> float:
        """Estimate cost based on pages processed."""
        model_pricing = MISTRAL_OCR_PRICING.get(
            self.model, 
            MISTRAL_OCR_PRICING["default"]
        )
        return (
            self.pages_processed * model_pricing["price_per_page_usd"]
            + self.annotated_pages_processed * model_pricing["price_per_annotated_page_usd"]
        )


@dataclass
class UsageStats:
    """Aggregated usage statistics for the entire session."""
    total_pages_processed: int = 0
    total_annotated_pages_processed: int = 0
    total_images_processed: int = 0
    total_document_api_calls: int = 0
    total_image_api_calls: int = 0
    total_bytes_processed: int = 0
    total_api_calls: int = 0
    estimated_cost_usd: float = 0.0
    models_used: Dict[str, int] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> float:
        """Duration in seconds."""
        if not self.start_time or not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def pages_per_second(self) -> float:
        """Pages processed per second."""
        if self.duration_seconds <= 0:
            return 0.0
        return self.total_pages_processed / self.duration_seconds
    
    def add_usage(self, usage_info: UsageInfo) -> None:
        """Add usage information from an API call."""
        self.total_pages_processed += usage_info.pages_processed
        self.total_annotated_pages_processed += usage_info.annotated_pages_processed
        self.total_bytes_processed += usage_info.doc_size_bytes
        self.total_document_api_calls += 1
        self.total_api_calls += 1
        self.estimated_cost_usd += usage_info.estimated_cost_usd
        
        # Track model usage
        if usage_info.model:
            self.models_used[usage_info.model] = self.models_used.get(usage_info.model, 0) + 1
    
    def add_image_usage(
        self,
        model: str = "mistral-ocr-latest",
        pages_processed: int = 1,
        annotated_pages_processed: int = 0,
    ) -> None:
        """Add usage for a single image OCR call."""
        model_pricing = MISTRAL_OCR_PRICING.get(
            model, 
            MISTRAL_OCR_PRICING["default"]
        )
        self.total_images_processed += 1
        self.total_image_api_calls += 1
        self.total_pages_processed += pages_processed
        self.total_annotated_pages_processed += annotated_pages_processed
        self.total_api_calls += 1
        self.estimated_cost_usd += (
            pages_processed * model_pricing["price_per_page_usd"]
            + annotated_pages_processed * model_pricing["price_per_annotated_page_usd"]
        )
        
        # Track model usage
        self.models_used[model] = self.models_used.get(model, 0) + 1
    
    def start(self) -> None:
        """Start the usage tracking session."""
        self.start_time = datetime.now()
    
    def end(self) -> None:
        """End the usage tracking session."""
        self.end_time = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_pages_processed": self.total_pages_processed,
            "document_annotated_pages_processed": self.total_annotated_pages_processed,
            "document_api_calls": self.total_document_api_calls,
            "image_api_calls": self.total_image_api_calls,
            "total_api_calls": self.total_api_calls,
            "total_images_processed": self.total_images_processed,
            "total_bytes_processed": self.total_bytes_processed,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "models_used": self.models_used,
            "duration_seconds": round(self.duration_seconds, 2),
            "pages_per_second": round(self.pages_per_second, 2),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }
    
    def save_to_file(self, path: Path) -> None:
        """Save usage statistics to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def print_summary(self) -> None:
        """Print a human-readable usage summary."""
        print("\n" + "=" * 60)
        print("💰 API Usage Summary")
        print("=" * 60)
        print(f"Total API calls:      {self.total_api_calls}")
        print(f"Document calls:       {self.total_document_api_calls}")
        print(f"Image calls:          {self.total_image_api_calls}")
        print(f"Pages processed:      {self.total_pages_processed}")
        print(f"Annotated pages:      {self.total_annotated_pages_processed}")
        print(f"Images processed:     {self.total_images_processed}")
        print(f"Total bytes:          {self.total_bytes_processed:,}")
        print(f"Duration:             {self.duration_seconds:.2f}s")
        print(f"Pages/second:        {self.pages_per_second:.2f}")
        print(f"Estimated cost:      ${self.estimated_cost_usd:.6f}")
        
        if self.models_used:
            print(f"\nModels used:")
            for model, count in self.models_used.items():
                print(f"  - {model}: {count} calls")
        
        print()


class UsageTracker:
    """Tracks API usage across the batch processing session.
    
    Provides:
    - Automatic extraction of usage_info from OCR responses
    - Cost estimation based on Mistral pricing
    - Usage statistics and reporting
    
    Attributes:
        stats: Aggregated usage statistics
    """
    
    def __init__(self):
        """Initialize usage tracker."""
        self.stats = UsageStats()
    
    def start(self) -> None:
        """Start tracking a new session."""
        self.stats = UsageStats()
        self.stats.start()
    
    def extract_usage_info(self, response: Any) -> UsageInfo:
        """Extract usage information from an OCR API response.
        
        Args:
            response: OCR API response object
        
        Returns:
            UsageInfo with extracted usage data
        """
        usage_info = UsageInfo()
        
        # Check for usage_info in response
        if hasattr(response, 'usage_info') and response.usage_info:
            usage_info.pages_processed = getattr(
                response.usage_info, 'pages_processed', 0
            )
            usage_info.annotated_pages_processed = getattr(
                response.usage_info, 'annotated_pages_processed', 0
            )
            usage_info.doc_size_bytes = getattr(
                response.usage_info, 'doc_size_bytes', 0
            )

        if not usage_info.pages_processed and hasattr(response, "pages"):
            usage_info.pages_processed = len(getattr(response, "pages", []) or [])
        
        # Get model from response
        if hasattr(response, 'model'):
            usage_info.model = response.model
        
        return usage_info
    
    def record_document_ocr(self, response: Any, model: str = None) -> None:
        """Record a document OCR API call.
        
        Args:
            response: OCR API response
            model: Model used (overrides response.model if provided)
        """
        usage_info = self.extract_usage_info(response)
        
        if model:
            usage_info.model = model
        
        self.stats.add_usage(usage_info)
    
    def record_image_ocr(self, response: Any = None, model: str = "mistral-ocr-latest") -> None:
        """Record an image OCR API call.
        
        Args:
            response: OCR API response
            model: Model used for image OCR
        """
        # Backward compatibility: allow record_image_ocr("model-name")
        if isinstance(response, str) and model == "mistral-ocr-latest":
            model = response
            response = None

        if response is not None:
            usage_info = self.extract_usage_info(response)
            if not usage_info.pages_processed:
                usage_info.pages_processed = 1
            if model:
                usage_info.model = model
            self.stats.add_usage(usage_info)
        else:
            self.stats.add_image_usage(model)
    
    def end(self) -> None:
        """End the tracking session."""
        self.stats.end()
    
    def get_stats(self) -> UsageStats:
        """Get the current usage statistics.
        
        Returns:
            UsageStats object
        """
        return self.stats
    
    def print_summary(self) -> None:
        """Print usage summary."""
        self.stats.print_summary()
    
    def save_to_file(self, path: Path) -> None:
        """Save usage statistics to a file.
        
        Args:
            path: Output file path
        """
        self.stats.save_to_file(path)
