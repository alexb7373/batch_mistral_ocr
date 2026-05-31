"""
Mistral OCR API client wrapper for Batch Processor.
"""

import time
from pathlib import Path
from typing import Optional, Any
from functools import wraps

from mistralai.client import Mistral
from mistralai.client.models import DocumentURLChunk, ImageURLChunk

from ..utils.usage_tracker import UsageTracker, UsageInfo
from src.utils.image_utils import ImageUtils


class OCRClient:
    """Wrapper for Mistral OCR API with retry logic and error handling.
    
    Provides a clean interface for:
    - Document OCR processing
    - Image OCR processing
    - File upload and signed URL generation
    
    Attributes:
        client: Mistral client instance
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    """
    
    def __init__(self, api_key: str, max_retries: int = 3, retry_delay: float = 1.0, 
                 usage_tracker: Optional[UsageTracker] = None):
        """Initialize OCR client.
        
        Args:
            api_key: Mistral API key
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Delay between retries in seconds (default: 1.0)
            usage_tracker: Optional UsageTracker for accounting (default: None)
        """
        self.client = Mistral(api_key=api_key)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.usage_tracker = usage_tracker
    
    def process_document(
        self,
        document_url: str,
        model: str = "mistral-ocr-latest",
        include_image_base64: bool = True
    ) -> Any:
        """Process a document with OCR.
        
        Args:
            document_url: URL of the document to process
            model: OCR model to use (default: mistral-ocr-latest)
            include_image_base64: Whether to include base64 image data (default: True)
        
        Returns:
            OCR response from Mistral API
        
        Raises:
            RuntimeError: If processing fails after all retries
        """
        response = self._retry_on_failure(
            self._process_document_inner,
            document_url=document_url,
            model=model,
            include_image_base64=include_image_base64
        )
        
        # Track usage if tracker is configured
        if self.usage_tracker:
            self.usage_tracker.record_document_ocr(response, model)
        
        return response
    
    def _process_document_inner(
        self,
        document_url: str,
        model: str,
        include_image_base64: bool
    ) -> Any:
        """Inner function for document processing (used by retry wrapper)."""
        response = self.client.ocr.process(
            document=DocumentURLChunk(document_url=document_url),
            model=model,
            include_image_base64=include_image_base64
        )
        return response
    
    def process_image(
        self,
        image_data: str,
        model: str = "mistral-ocr-latest"
    ) -> Any:
        """Process an image with OCR.
        
        Args:
            image_data: Base64 encoded image data (with or without data URL header)
            model: OCR model to use (default: mistral-ocr-latest)
        
        Returns:
            OCR response from Mistral API
        
        Raises:
            RuntimeError: If processing fails after all retries
        """
        # Accept either raw base64 data or a full data URL.
        if image_data.startswith("data:") and ";base64," in image_data:
            image_url = image_data
        else:
            img_format = ImageUtils.detect_format(image_data)
            image_url = ImageUtils.create_data_url(img_format.mime_type, image_data)
        
        response = self._retry_on_failure(
            self._process_image_inner,
            image_url=image_url,
            model=model
        )
        
        # Track usage if tracker is configured
        if self.usage_tracker:
            self.usage_tracker.record_image_ocr(response, model)
        
        return response

    def describe_image(
        self,
        image_data: str,
        prompt: str,
        model: str = "pixtral-12b-2409",
    ) -> str:
        """Analyze an image with a multimodal chat model.

        Args:
            image_data: Base64 data or data URL for the image
            prompt: Instruction for the vision model
            model: Vision/chat model to use

        Returns:
            Generated text from the vision model
        """
        if image_data.startswith("data:") and ";base64," in image_data:
            image_url = image_data
        else:
            img_format = ImageUtils.detect_format(image_data)
            image_url = ImageUtils.create_data_url(img_format.mime_type, image_data)

        response = self._retry_on_failure(
            self._describe_image_inner,
            image_url=image_url,
            prompt=prompt,
            model=model,
        )
        return self._extract_chat_content(response)

    def _describe_image_inner(self, image_url: str, prompt: str, model: str) -> Any:
        """Inner function for multimodal chat image analysis."""
        return self.client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": image_url},
                    ],
                }
            ],
        )
    
    def _process_image_inner(self, image_url: str, model: str) -> Any:
        """Inner function for image processing (used by retry wrapper)."""
        response = self.client.ocr.process(
            document=ImageURLChunk(image_url=image_url),
            model=model,
            include_image_base64=False
        )
        return response

    @staticmethod
    def _extract_chat_content(response: Any) -> str:
        """Extract message content from a chat completion response."""
        try:
            content = response.choices[0].message.content
        except Exception:
            return ""

        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
                else:
                    parts.append(str(item))
            return "".join(parts).strip()

        return str(content).strip()
    
    def upload_file(self, file_path: Path, purpose: str = "ocr") -> str:
        """Upload a file and return signed URL.
        
        Args:
            file_path: Path to the file to upload
            purpose: Purpose of the upload (default: ocr)
        
        Returns:
            Signed URL for accessing the uploaded file
        
        Raises:
            RuntimeError: If upload fails after all retries
        """
        return self._retry_on_failure(
            self._upload_file_inner,
            file_path=file_path,
            purpose=purpose
        )
    
    def _upload_file_inner(self, file_path: Path, purpose: str) -> str:
        """Inner function for file upload (used by retry wrapper)."""
        uploaded = self.client.files.upload(
            file={"file_name": file_path.stem, "content": file_path.read_bytes()},
            purpose=purpose,
        )
        signed_url = self.client.files.get_signed_url(file_id=uploaded.id, expiry=1)
        return signed_url.url
    
    def _retry_on_failure(self, func, *args, **kwargs) -> Any:
        """Retry a function call on failure.
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Result of the function call
        
        Raises:
            RuntimeError: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    # Wait before retrying
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    # All retries failed
                    raise RuntimeError(
                        f"Operation failed after {self.max_retries + 1} attempts. "
                        f"Last error: {last_exception}"
                    ) from last_exception
        
        # Should not reach here, but just in case
        raise RuntimeError("Unexpected error in retry logic")
