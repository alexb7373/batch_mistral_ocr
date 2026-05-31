"""
PDF and Image processors for Mistral OCR Batch Processor.
"""

import re
from pathlib import Path
from typing import Optional, List

from .client import OCRClient
from .diagram_extractor import DiagramExtractor
from src.utils.file_utils import FileUtils
from src.utils.image_utils import ImageUtils
from src.models.types import ProcessResult, OCRPage, OCRImage


class PDFProcessor:
    """Process PDF documents through OCR.
    
    Handles:
    - PDF file upload
    - Document OCR processing
    - Image extraction from pages
    - Markdown output generation
    
    Attributes:
        client: OCRClient instance
        config: Configuration object with input_dir, output_dir, etc.
        diagram_extractor: DiagramExtractor instance
    """
    
    def __init__(self, client: OCRClient, config):
        """Initialize PDF processor.
        
        Args:
            client: OCRClient instance
            config: Configuration object with input_dir, output_dir, regular_model, etc.
        """
        self.client = client
        self.config = config
        self.diagram_extractor = DiagramExtractor(client)
    
    def process(self, pdf_path: Path) -> ProcessResult:
        """Process a single PDF file.
        
        Args:
            pdf_path: Path to the PDF file
        
        Returns:
            ProcessResult with success status and metadata
        """
        base_filename = pdf_path.stem
        md_file = FileUtils.get_unique_output_path(
            pdf_path, 
            self.config.output_dir, 
            extension=".md"
        )
        
        # Check if already processed (unless force_reprocess is True)
        if not self.config.force_reprocess and FileUtils.file_exists(md_file):
            return ProcessResult(
                success=True,
                output_path=md_file,
                skipped=True
            )
        
        try:
            # Upload PDF
            signed_url = self.client.upload_file(pdf_path, purpose="ocr")
            
            # Process with OCR
            response = self.client.process_document(
                signed_url,
                model=self.config.regular_model,
                include_image_base64=True
            )
            
            # Process pages
            md_output = []
            images_processed = 0
            diagrams_extracted = 0
            
            for page in response.pages:
                page_content, page_images, page_diagrams = self._process_page(
                    page, 
                    base_filename
                )
                md_output.append(page_content)
                images_processed += page_images
                diagrams_extracted += page_diagrams
            
            # Write output
            FileUtils.write_text(md_file, "\n\n".join(md_output))
            
            return ProcessResult(
                success=True,
                output_path=md_file,
                images_processed=images_processed,
                pages_processed=len(response.pages),
                diagrams_extracted=diagrams_extracted
            )
        
        except Exception as e:
            return ProcessResult(
                success=False,
                error=str(e)
            )
    
    def _process_page(self, page, base_filename: str) -> tuple[str, int, int]:
        """Process a single page from OCR response.
        
        Args:
            page: OCR page object from Mistral API
            base_filename: Base filename (without extension)
        
        Returns:
            tuple: (page_markdown, images_processed_count, diagrams_extracted_count)
        """
        page_index = page.index
        page_tag = f"{base_filename}_Page_{page_index:03}"
        
        markdown_parts = [f"---{page_tag}_start---\n"]
        images_processed = 0
        diagrams_extracted = 0
        
        # Process images if present
        if hasattr(page, "images") and isinstance(page.images, list):
            for i, img_obj in enumerate(page.images):
                img_result = self._process_image(
                    img_obj, 
                    page_index, 
                    i, 
                    base_filename
                )
                if img_result:
                    images_processed += 1
                    if img_result[1]:  # Diagram was extracted
                        diagrams_extracted += 1
        
        # Add page markdown
        page_md = getattr(page, "markdown", "")
        if page_md:
            markdown_parts.append(page_md)
        
        markdown_parts.append(f"---{page_tag}_end---\n")
        
        return ("\n".join(markdown_parts), images_processed, diagrams_extracted)
    
    def _process_image(
        self, 
        img_obj, 
        page_index: int, 
        image_index: int, 
        base_filename: str
    ) -> tuple[Optional[str], bool]:
        """Process a single image from a page.
        
        Args:
            img_obj: Image object from Mistral OCR response
            page_index: Page index
            image_index: Image index on page
            base_filename: Base filename for output paths
        
        Returns:
            tuple: (updated_markdown, is_diagram)
        """
        try:
            if not hasattr(img_obj, "image_base64") or not img_obj.image_base64:
                return None, False
            
            # Split base64 header if present
            if "," in img_obj.image_base64:
                _, b64_data = img_obj.image_base64.split(",", 1)
            else:
                b64_data = img_obj.image_base64
            
            # Detect image format
            img_format = ImageUtils.detect_format(b64_data)
            ext = ImageUtils.get_extension(img_format)
            
            # Create image directory
            img_dir = self.config.output_dir / base_filename
            FileUtils.ensure_directory(img_dir)
            
            # Save image
            img_filename = f"page{page_index:03}_image{image_index}{ext}"
            img_path = img_dir / img_filename
            image_bytes = ImageUtils.decode_base64(img_obj.image_base64)
            FileUtils.save_image(image_bytes, img_path)
            
            # Try diagram extraction first
            diagram_text = self.diagram_extractor.extract_from_base64(img_obj.image_base64)
            
            # Get page markdown
            page_md = getattr(img_obj, "parent", {}).markdown if hasattr(img_obj, "parent") else ""
            
            # Update markdown references
            if page_md:
                # Replace image references
                page_md = self._replace_image_references(page_md, img_obj, img_filename, base_filename)
            
            # Add OCR text if available
            if diagram_text:
                page_md = f"{page_md}\n\n**OCR Extracted Diagram:**\n{img_filename}\n{diagram_text}"
                return page_md, True
            else:
                # Try regular OCR on the saved image
                ocr_text = self._ocr_image(img_path)
                if ocr_text and ocr_text.strip():
                    page_md = f"{page_md}\n\n**OCR Extracted Text from image:**\n{img_filename}\n{ocr_text.strip()}"
                return page_md, False
            
            return page_md, False
        
        except Exception as e:
            print(f"  ❌ Error processing image {image_index}: {e}")
            return None, False
    
    def _replace_image_references(
        self, 
        markdown: str, 
        img_obj, 
        img_filename: str, 
        base_filename: str
    ) -> str:
        """Replace image references in markdown with actual file paths.
        
        Args:
            markdown: Page markdown content
            img_obj: Image object
            img_filename: Output image filename
            base_filename: Base filename for path
        
        Returns:
            Updated markdown with correct image paths
        """
        if not markdown:
            return markdown
        
        # Get image ID if available
        img_id = getattr(img_obj, "id", None)
        
        if img_id:
            # Try various patterns
            patterns = [
                f"![]({img_id})",
                f"![{img_id}]({img_id})",
                f"[{img_id}]({img_id})",
            ]
            replacement = f"![]({base_filename}/{img_filename})"
            for pattern in patterns:
                markdown = markdown.replace(pattern, replacement)
        
        # Also try index-based patterns
        markdown = markdown.replace(
            f"![](img-{image_index})",
            f"![]({base_filename}/{img_filename})"
        )
        
        return markdown
    
    def _ocr_image(self, image_path: Path) -> Optional[str]:
        """Perform OCR on a single image file.
        
        Args:
            image_path: Path to the image file
        
        Returns:
            Extracted text or None
        """
        try:
            # Read image
            image_data = image_path.read_bytes()
            import base64
            encoded = base64.b64encode(image_data).decode("utf-8")
            
            # Detect format
            img_format = ImageUtils.detect_format(encoded)
            data_url = f"data:{img_format.mime_type};base64,{encoded}"
            
            # Process with OCR
            response = self.client.process_image(data_url, model=self.config.regular_model)
            
            if response.pages and len(response.pages) > 0:
                markdown = response.pages[0].markdown.strip()
                # Clean up any self-referencing image links
                markdown = re.sub(r'\[.*?\]\(.*?\)', '', markdown)
                return "\n" + markdown + "\n" if markdown else ""
            return ""
        
        except Exception as e:
            print(f"⚠️  OCR failed for image {image_path.name}: {e}")
            return ""


class ImageProcessor:
    """Standalone image processor.
    
    Used for processing individual images that may not be part of a PDF.
    
    Attributes:
        client: OCRClient instance
        diagram_extractor: DiagramExtractor instance
    """
    
    def __init__(self, client: OCRClient):
        """Initialize image processor.
        
        Args:
            client: OCRClient instance
        """
        self.client = client
        self.diagram_extractor = DiagramExtractor(client)
    
    def process(self, image_path: Path) -> Optional[str]:
        """Process a single image file.
        
        Attempts diagram extraction first, then falls back to regular OCR.
        
        Args:
            image_path: Path to the image file
        
        Returns:
            Extracted text (diagram or OCR) or None
        """
        # Try diagram extraction first
        diagram_text = self.diagram_extractor.extract(image_path)
        if diagram_text:
            return diagram_text
        
        # Fall back to regular OCR
        return self.ocr_image(image_path)
    
    def ocr_image(self, image_path: Path) -> Optional[str]:
        """Perform regular OCR on an image.
        
        Args:
            image_path: Path to the image file
        
        Returns:
            Extracted text or None
        """
        try:
            # Read image
            image_data = image_path.read_bytes()
            import base64
            encoded = base64.b64encode(image_data).decode("utf-8")
            
            # Detect format
            img_format = ImageUtils.detect_format(encoded)
            data_url = f"data:{img_format.mime_type};base64,{encoded}"
            
            # Process with OCR
            response = self.client.process_image(data_url, model="mistral-ocr-latest")
            
            if response.pages and len(response.pages) > 0:
                markdown = response.pages[0].markdown.strip()
                # Clean up
                markdown = re.sub(r'\[.*?\]\(.*?\)', '', markdown)
                return "\n" + markdown + "\n" if markdown else ""
            return ""
        
        except Exception as e:
            print(f"⚠️  OCR failed for image {image_path.name}: {e}")
            return ""
