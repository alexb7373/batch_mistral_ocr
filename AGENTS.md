# Agent Instructions for batch_mistral_ocr

## Environment Setup

Before running any scripts, activate the virtual environment:

```bash
source ../.venv/bin/activate
```

This ensures all dependencies (mistralai, python-dotenv) are available.

## Important Notes

- The `.env` file is located at `../.env` (parent directory)
- API key is loaded from: environment variable → `../.env` → `./.env`
- Input directory can be configured via `config/config.py` or uses `pdfs/` by default
- Output directory can be configured via `config/config.py` or uses `output/` by default

## Workflow

1. Activate venv: `source ../.venv/bin/activate`
2. Run the local batch script: `python ocr_batch.py`
3. Run the workspace/books CLI when needed: `python book_ocr.py --all`
