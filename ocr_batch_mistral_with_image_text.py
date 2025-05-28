import os
import base64
from pathlib import Path
from mistralai import Mistral, DocumentURLChunk, ImageURLChunk
from config.config import INPUT_DIR, OUTPUT_DIR  # ✅ import your paths


# Configuration
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load API key from environment variable
api_key = os.getenv("MISTRAL_API_KEY")
if not api_key:
    raise EnvironmentError("MISTRAL_API_KEY environment variable not set")

# Initialize client
client = Mistral(api_key=api_key)

def ocr_image_to_text(image_path: Path):
    with open(image_path, "rb") as img_file:
        encoded_img = base64.b64encode(img_file.read()).decode("utf-8")
    image_url = f"data:image/jpeg;base64,{encoded_img}"
    try:
        response = client.ocr.process(
            model="mistral-ocr-latest",
            document=ImageURLChunk(image_url=image_url),
            include_image_base64=False
        )
        return "\n" + response.pages[0].markdown.strip() + "\n"
    except Exception as e:
        print(f"⚠️ OCR failed for image {image_path.name}: {e}")
        return ""

def process_pdf(pdf_path: Path):
    base_filename = pdf_path.stem
    md_file = OUTPUT_DIR / f"{base_filename}.md"

    if md_file.exists():
        print(f"⏭️ Skipping {pdf_path.name}, already processed.")
        return

    print(f"🔍 Processing {pdf_path.name}")
    try:
        uploaded = client.files.upload(
            file={"file_name": pdf_path.stem, "content": pdf_path.read_bytes()},
            purpose="ocr",
        )
        signed_url = client.files.get_signed_url(file_id=uploaded.id, expiry=1)
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

            if hasattr(page, "images") and isinstance(page.images, list):
                for i, img_obj in enumerate(page.images):
                    try:
                        if not hasattr(img_obj, "image_base64") or not img_obj.image_base64:
                            continue

                        _, b64_data = img_obj.image_base64.split(",", 1)
                        ext = ".jpeg"

                        img_dir = OUTPUT_DIR / base_filename
                        img_dir.mkdir(parents=True, exist_ok=True)

                        img_filename = f"page{page_index:03}_image{i}{ext}"
                        img_path = img_dir / img_filename
                        with open(img_path, "wb") as f:
                            f.write(base64.b64decode(b64_data))

                        # Replace image markdown and append OCR text if possible
                        if hasattr(page, "markdown"):
                            original_img_id = getattr(img_obj, "id", f"img_{page_index}_{i}")
                            page.markdown = (
                                page.markdown
                                .replace(f"![]({original_img_id})", f"![]({base_filename}/{img_filename})")
                                .replace(f"![{original_img_id}]({original_img_id})", f"![]({base_filename}/{img_filename})")
                            )

                        ocr_text = ocr_image_to_text(img_path)
                        if ocr_text:
                            page.markdown += f"\n\n**OCR Extracted Text from image:**\n{ocr_text}"

                    except Exception as e:
                        print(f"❌ Error processing image {i} on page {page_index} of {pdf_path.name}: {e}")

            md_output.append(page.markdown)
            md_output.append(f"---{page_tag}_end---\n")

        md_file.write_text("\n\n".join(md_output), encoding="utf-8")
        print(f"✅ Saved: {md_file}")

    except Exception as e:
        print(f"❌ Failed {pdf_path.name}: {e}")

# Process all PDFs
for pdf_file in INPUT_DIR.glob("*.pdf"):
    process_pdf(pdf_file)