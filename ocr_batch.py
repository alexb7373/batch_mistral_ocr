#!/usr/bin/env python3
"""
Batch OCR processor for PDF documents using Mistral OCR API.
Extracts Markdown per page and handles embedded images by saving them
and performing OCR on those as well.
"""

import os
import base64
import re
from pathlib import Path
from typing import Optional

from mistralai import Mistral, DocumentURLChunk, ImageURLChunk

try:
    from dotenv import load_dotenv
except ImportError:
    print("⚠️  python-dotenv not installed. Using environment variables only.")
    load_dotenv = None


# --- Configuration ---

def load_config() -> tuple[Path, Path]:
    """Load input and output directories from config or use defaults."""
    # Try to import from config/config.py if it exists
    config_path = Path("config/config.py")
    if config_path.exists():
        try:
            from config.config import INPUT_DIR, OUTPUT_DIR
            input_dir = Path(INPUT_DIR)
            output_dir = Path(OUTPUT_DIR)
            print(f"📂 Config loaded: {input_dir} -> {output_dir}")
            return input_dir, output_dir
        except Exception as e:
            print(f"⚠️  Could not load config/config.py: {e}")
    
    # Fallback to defaults
    input_dir = Path("pdfs")
    output_dir = Path("output")
    print(f"📂 Using default directories: {input_dir} -> {output_dir}")
    return input_dir, output_dir


# Load directories
INPUT_DIR, OUTPUT_DIR = load_config()

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --- Environment Setup ---

def load_api_key() -> str:
    """Load Mistral API key from environment or .env file."""
    # Check if already in environment
    api_key = os.getenv("MISTRAL_API_KEY")
    if api_key:
        return api_key
    
    # Try loading from ../.env (parent directory)
    parent_env = Path("../.env")
    if parent_env.exists():
        if load_dotenv:
            load_dotenv(dotenv_path=parent_env)
            api_key = os.getenv("MISTRAL_API_KEY")
            if api_key:
                return api_key
    
    # Try loading from ./.env (project directory)
    local_env = Path("./.env")
    if local_env.exists():
        if load_dotenv:
            load_dotenv(dotenv_path=local_env)
            api_key = os.getenv("MISTRAL_API_KEY")
            if api_key:
                return api_key
    
    raise EnvironmentError(
        "MISTRAL_API_KEY not found. "
        "Set it in your environment or create a .env file in the project root or parent directory."
    )


# Load API key
try:
    api_key = load_api_key()
except EnvironmentError as e:
    print(f"❌ {e}")
    exit(1)

print(f"🔑 API key loaded successfully")

# Initialize client
client = Mistral(api_key=api_key)


# --- Helper Functions ---

def detect_image_format(b64_data: str) -> tuple[str, str]:
    """
    Detect image format from base64 data.
    Returns (mime_type, extension)
    """
    # Common base64 headers
    format_signatures = {
        b'\x89PNG\r\n\x1a\n': ('image/png', '.png'),
        b'\xff\xd8\xff': ('image/jpeg', '.jpeg'),
        b'\x47\x49\x46\x38': ('image/gif', '.gif'),
        b'RIFF': ('image/webp', '.webp'),
        b'BM': ('image/bmp', '.bmp'),
    }
    
    try:
        # Decode a small portion to check signature
        raw_data = base64.b64decode(b64_data[:100])
        for signature, (mime, ext) in format_signatures.items():
            if raw_data.startswith(signature):
                return mime, ext
    except Exception:
        pass
    
    # Default to jpeg if we can't detect
    print("⚠️  Could not detect image format, defaulting to jpeg")
    return 'image/jpeg', '.jpeg'


def ocr_image_to_text(image_path: Path) -> str:
    """Perform OCR on a single image file."""
    if not image_path.exists():
        print(f"⚠️  Image not found: {image_path}")
        return ""
    
    try:
        with open(image_path, "rb") as img_file:
            encoded_img = base64.b64encode(img_file.read()).decode("utf-8")
        
        # Detect format for proper MIME type
        mime_type, _ = detect_image_format(encoded_img)
        image_url = f"{mime_type};base64,{encoded_img}"
        
        response = client.ocr.process(
            model="mistral-ocr-latest",
            document=ImageURLChunk(image_url=image_url),
            include_image_base64=False
        )
        
        if response.pages and len(response.pages) > 0:
            markdown = response.pages[0].markdown.strip()
            # Clean up any self-referencing image links from OCR
            # Remove patterns like ![](image.jpg) or [image.jpg](image.jpg)
            markdown = re.sub(r'\[.*?\]\(.*?\)', '', markdown)
            return "\n" + markdown + "\n" if markdown else ""
        return ""
    
    except Exception as e:
        print(f"⚠️  OCR failed for image {image_path.name}: {e}")
        return ""


def get_image_id_from_markdown(markdown: str, img_obj) -> Optional[str]:
    """Extract the image ID used in markdown from the image object."""
    if not markdown:
        return None
    
    # Try to find the image reference in markdown
    # Common patterns: ![](id), ![alt](id), [](id)
    img_id = getattr(img_obj, 'id', None)
    if img_id and f"{img_id}" in markdown:
        return img_id
    
    # If we can't find a specific ID, generate one
    return None


def process_pdf(pdf_path: Path) -> bool:
    """Process a single PDF file. Returns True if successful."""
    base_filename = pdf_path.stem
    md_file = OUTPUT_DIR / f"{base_filename}.md"
    
    if md_file.exists():
        print(f"⏭️  Skipping {pdf_path.name}, already processed.")
        return True
    
    print(f"🔍 Processing {pdf_path.name}")
    
    try:
        # Upload PDF
        uploaded = client.files.upload(
            file={"file_name": pdf_path.stem, "content": pdf_path.read_bytes()},
            purpose="ocr",
        )
        
        # Get signed URL
        signed_url = client.files.get_signed_url(file_id=uploaded.id, expiry=1)
        
        # Process with OCR
        response = client.ocr.process(
            document=DocumentURLChunk(document_url=signed_url.url),
            model="mistral-ocr-latest",
            include_image_base64=True
        )
        
        md_output = []
        
        for page in response.pages:
            page_index = page.index
            page_tag = f"{base_filename}_Page_{page_index:03}"
            md_output.append(f"---{page_tag}_start---\n")
            
            # Process images if present
            if hasattr(page, "images") and isinstance(page.images, list):
                for i, img_obj in enumerate(page.images):
                    try:
                        if not hasattr(img_obj, "image_base64") or not img_obj.image_base64:
                            continue
                        
                        # Split base64 header if present
                        if "," in img_obj.image_base64:
                            _, b64_data = img_obj.image_base64.split(",", 1)
                        else:
                            b64_data = img_obj.image_base64
                        
                        # Detect image format
                        mime_type, ext = detect_image_format(b64_data)
                        
                        # Create image directory
                        img_dir = OUTPUT_DIR / base_filename
                        img_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Save image
                        img_filename = f"page{page_index:03}_image{i}{ext}"
                        img_path = img_dir / img_filename
                        with open(img_path, "wb") as f:
                            f.write(base64.b64decode(b64_data))
                        
                        print(f"  🖼️  Saved image: {img_filename}")
                        
                        # Update markdown references
                        if hasattr(page, "markdown") and page.markdown:
                            # Get the image ID used in the markdown
                            img_id = get_image_id_from_markdown(page.markdown, img_obj)
                            
                            if img_id:
                                # Replace all variations of image references
                                patterns = [
                                    f"![]({img_id})",
                                    f"![{img_id}]({img_id})",
                                    f"[{img_id}]({img_id})",
                                ]
                                replacement = f"![]({base_filename}/{img_filename})"
                                for pattern in patterns:
                                    page.markdown = page.markdown.replace(pattern, replacement)
                            else:
                                # If we can't find the ID, try to replace generic patterns
                                page.markdown = page.markdown.replace(
                                    f"![](img-{i})", 
                                    f"![]({base_filename}/{img_filename})"
                                )
                        
                        # Perform OCR on the image
                        ocr_text = ocr_image_to_text(img_path)
                        if ocr_text and ocr_text.strip():
                            # Clean up the OCR text
                            ocr_text = ocr_text.strip()
                            page.markdown = (
                                page.markdown + 
                                f"\n\n**OCR Extracted Text from image:**\n{img_filename}\n{ocr_text}"
                            )
                    
                    except Exception as e:
                        print(f"  ❌ Error processing image {i} on page {page_index} of {pdf_path.name}: {e}")
            
            # Ensure markdown exists
            page_md = getattr(page, "markdown", "")
            if page_md:
                md_output.append(page_md)
            
            md_output.append(f"---{page_tag}_end---\n")
        
        # Write output
        md_file.write_text("\n\n".join(md_output), encoding="utf-8")
        print(f"✅ Saved: {md_file}")
        return True
    
    except Exception as e:
        print(f"❌ Failed {pdf_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    print("=" * 60)
    print("🚀 Mistral OCR Batch Processor")
    print("=" * 60)
    print(f"Input:  {INPUT_DIR.absolute()}")
    print(f"Output: {OUTPUT_DIR.absolute()}")
    print()
    
    # Track results
    processed = 0
    succeeded = 0
    failed = 0
    skipped = 0
    
    # Find all PDFs
    pdf_files = list(INPUT_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print("⚠️  No PDF files found in input directory.")
        return
    
    print(f"📚 Found {len(pdf_files)} PDF(s) to process\n")
    
    for pdf_file in sorted(pdf_files):
        result = process_pdf(pdf_file)
        processed += 1
        
        if result is None:
            skipped += 1
        elif result:
            succeeded += 1
        else:
            failed += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Processing Summary")
    print("=" * 60)
    print(f"Total PDFs found:  {len(pdf_files)}")
    print(f"✅ Processed:      {succeeded}")
    print(f"⏭️  Skipped:       {skipped}")
    print(f"❌ Failed:         {failed}")
    
    if failed > 0:
        print("\n⚠️  Some files failed. Check the error messages above.")
    
    print("\nDone! ✨")


if __name__ == "__main__":
    main()
