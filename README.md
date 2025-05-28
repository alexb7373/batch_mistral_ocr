# 🧾 Mistral OCR Batch Processor

This tool batch-processes PDF documents using the **Mistral OCR API**, extracts Markdown per page, and handles embedded images by saving them and performing OCR on those as well.

---

## 📁 Folder Structure

```
project-root/
├── config/
│   └── config.py         # Local path config (git-ignored)
├── pdfs/                 # Input folder for PDFs
├── output/               # Output folder for markdown and images
├── ocr_batch.py          # Main OCR batch processor
└── README.md             # This file
```

---

## ⚙️ Setup

1. **Clone the repository**

2. **Install required dependencies**
   ```bash
   pip install mistralai
   ```

3. **Add your API key**
   You can set the `MISTRAL_API_KEY` using:

   - **Linux/macOS**
     ```bash
     export MISTRAL_API_KEY=your_actual_api_key
     ```

   - **Windows CMD**
     ```cmd
     set MISTRAL_API_KEY=your_actual_api_key
     ```

   - **Windows PowerShell**
     ```powershell
     $env:MISTRAL_API_KEY="your_actual_api_key"
     ```

4. **Create config file**
   Create a file at `config/config.py`:

   ```python
   from pathlib import Path

   # On Windows use raw string (with r"") to avoid escaping backslashes
   INPUT_DIR = Path(r"C:\Users\user\Desktop\pdf_files")
   OUTPUT_DIR = Path(r"C:\Users\user\Desktop\pdf_files\out")
   ```

   Add `config/` to your `.gitignore` to keep local paths out of version control.

---

## 🚀 Run the Script

```bash
python ocr_batch.py
```

It will:

- Process all PDFs in the `INPUT_DIR`
- Output a `.md` file per PDF into the `OUTPUT_DIR`
- Save all detected images as `.jpeg`
- OCR image content and embed it in the markdown below the image reference

---

## ✅ Markdown Format

Each output Markdown file contains:

- `---filename_Page_N_start---` and `---filename_Page_N_end---` delimiters
- `![]()` links to extracted images
- Optional: `**OCR Extracted Text from image:**` section if image text is detected

---

## ❓FAQ

### What formats are supported?
PDF input, JPEG image OCR output.

### Can I run this headlessly on a server?
Yes. Just set the `MISTRAL_API_KEY` and run the script.

### Can I use other image formats?
Yes, with small code tweaks (e.g., detecting `png`, `webp` from base64 header).

---

## 🔗 Resources & References

- 📄 [Basic OCR - Mistral Docs](https://docs.mistral.ai/capabilities/OCR/basic_ocr/)
- 📰 [Mistral OCR Announcement](https://mistral.ai/news/mistral-ocr)
- 🎓 Inspired by: [Mistral Structured OCR Colab Notebook](https://colab.research.google.com/github/mistralai/cookbook/blob/main/mistral/ocr/structured_ocr.ipynb)

---

## 🛡️ Disclaimer

This repo is a personal utility. Use Mistral OCR responsibly according to your usage plan.