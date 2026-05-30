# 🧾 Mistral OCR Batch Processor

This tool batch-processes PDF documents using the **Mistral OCR API**, extracts Markdown per page, and handles embedded images by saving them and performing OCR on those as well.

Markdown is useful for feeding the documents into RAG. Markdown works especially well for tables, and mathematical formulas, given Mistral OCR is really good at processing those. 

---

## 📁 Folder Structure

```
project-root/
├── config/
│   └── config.py         # Local path config (git-ignored)
├── pdfs/                 # Input folder for PDFs
├── output/               # Output folder for markdown and images
├── ocr_batch.py          # Main OCR batch processor
├── requirements.txt      # Python dependencies
├── AGENTS.md            # Agent-specific instructions
└── README.md             # This file
```

---

## ⚙️ Setup

1. **Clone the repository**

2. **Install required dependencies**
   
   Using a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   pip install -r requirements.txt
   ```
   
   Or install globally (may require `--break-system-packages` on some systems):
   ```bash
   pip install mistralai python-dotenv
   ```

3. **Add your API key**

   The script will look for the `MISTRAL_API_KEY` in this order:
   1. Environment variable (already set)
   2. `../.env` (parent directory)
   3. `./.env` (project directory)

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

   - **Using .env file** (recommended)
     Create a `.env` file in `~/projects/.env` (or in the project root):
     ```
     MISTRAL_API_KEY=your_actual_api_key
     ```

4. **Create config file (optional)**
   Create a file at `config/config.py`:

   ```python
   from pathlib import Path

   # On Windows use raw string (with r"") to avoid escaping backslashes
   INPUT_DIR = r"C:\Users\user\Desktop\pdf_files"  # add .replace('C:\\', '/mnt/c/').replace('\\','/') for WSL
   OUTPUT_DIR = r"C:\Users\user\Desktop\pdf_files\out"
   ```

   If you don't create this file, the script will use default directories:
   - Input: `pdfs/`
   - Output: `output/`

   Add `config/` to your `.gitignore` to keep local paths out of version control.

---

## 🚀 Run the Script

```bash
python ocr_batch.py
```

It will:

- Process all PDFs in the `INPUT_DIR`
- Output a `.md` file per PDF into the `OUTPUT_DIR`
- Save all detected images with their correct format (PNG, JPEG, etc.)
- OCR image content and embed it in the markdown below the image reference
- Provide a summary of processed, skipped, and failed files

---

## ✅ Markdown Format

Each output Markdown file contains:

- `---filename_Page_N_start---` and `---filename_Page_N_end---` delimiters
- `![]()` links to extracted images
- Optional: `**OCR Extracted Text from image:**` section if image text is detected

---

## ❓FAQ

### What formats are supported?
PDF input, PNG/JPEG/GIF/WebP image OCR output (auto-detected).

### Can I run this headlessly on a server?
Yes. Just set the `MISTRAL_API_KEY` and run the script.

### Can I use other image formats?
Yes! The script now automatically detects image formats (PNG, JPEG, GIF, WebP, BMP) from the base64 data and saves them with the correct extension.

### The script crashes with "config/config.py not found"
No problem! The script will fall back to using `pdfs/` as input and `output/` as output directories. You can also create the config file as shown above.

---

## 📊 Features

- **Automatic image format detection** - No more hardcoded JPEG assumptions
- **Flexible configuration** - Uses config file if present, defaults otherwise
- **Multiple .env locations** - Checks parent directory, project directory, or environment variable
- **Graceful error handling** - Continues processing other files if one fails
- **Progress tracking** - Shows summary of processed, skipped, and failed files
- **Robust markdown processing** - Handles missing markdown and null values safely

---

## 🔗 Resources & References

- 📄 [Basic OCR - Mistral Docs](https://docs.mistral.ai/capabilities/OCR/basic_ocr/)
- 📰 [Mistral OCR Announcement](https://mistral.ai/news/mistral-ocr)
- 🎓 Inspired by: [Mistral Structured OCR Colab Notebook](https://colab.research.google.com/github/mistralai/cookbook/blob/main/mistral/ocr/structured_ocr.ipynb)

---

## 🛡️ Disclaimer

This repo is a personal utility. Use Mistral OCR responsibly according to your usage plan.
