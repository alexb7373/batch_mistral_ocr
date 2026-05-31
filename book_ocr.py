#!/usr/bin/env python3
"""
OCR book PDFs from ../books into ../books/ocr.

Examples:
    python book_ocr.py ../books/whoNeedsArchitect.pdf
    python book_ocr.py --all --register-rag
"""

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import AppConfig, load_api_key
from src.ocr.client import OCRClient
from src.ocr.processors import PDFProcessor
from src.utils.logging import ProgressTracker


DEFAULT_BOOKS_DIR = WORKSPACE_ROOT / "books"
DEFAULT_OCR_DIR = DEFAULT_BOOKS_DIR / "ocr"
DEFAULT_RAG_DIR = WORKSPACE_ROOT / "aiar-rdcz-1" / "ai-framework" / "knowledge-base" / "books"


def _resolve_pdf(path: Path, books_dir: Path) -> Path:
    if path.exists():
        return path.resolve()
    candidate = books_dir / path
    if candidate.exists():
        return candidate.resolve()
    raise FileNotFoundError(f"PDF not found: {path}")


def _selected_pdfs(args: argparse.Namespace, books_dir: Path) -> list[Path]:
    if args.all:
        return sorted(p.resolve() for p in books_dir.glob("*.pdf"))
    if not args.pdfs:
        raise ValueError("Pass one or more PDFs, or use --all.")
    return [_resolve_pdf(Path(pdf), books_dir) for pdf in args.pdfs]


def _build_config(output_dir: Path, force: bool, verbose: bool) -> AppConfig:
    return AppConfig(
        input_dir=DEFAULT_BOOKS_DIR,
        output_dir=output_dir,
        api_key=load_api_key(),
        force_reprocess=force,
        verbose=verbose,
    )


def _register_for_rag(markdown_path: Path, rag_dir: Path) -> Path:
    rag_dir.mkdir(parents=True, exist_ok=True)
    target = rag_dir / markdown_path.name
    shutil.copy2(markdown_path, target)
    image_dir = markdown_path.parent / markdown_path.stem
    if image_dir.exists():
        shutil.copytree(image_dir, rag_dir / image_dir.name, dirs_exist_ok=True)
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OCR book PDFs to books/ocr/<book>.md plus extracted images."
    )
    parser.add_argument("pdfs", nargs="*", help="PDF paths or filenames under books/.")
    parser.add_argument("--all", action="store_true", help="Process every PDF directly under books/.")
    parser.add_argument("--books-dir", type=Path, default=DEFAULT_BOOKS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OCR_DIR)
    parser.add_argument("--force", action="store_true", help="Reprocess even if markdown already exists.")
    parser.add_argument("--quiet", action="store_true", help="Reduce progress logging.")
    parser.add_argument(
        "--register-rag",
        action="store_true",
        help="Copy generated markdown into the AI framework knowledge-base/books directory.",
    )
    parser.add_argument(
        "--rag-dir",
        type=Path,
        default=DEFAULT_RAG_DIR,
        help="Target directory used with --register-rag.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    books_dir = args.books_dir.resolve()
    output_dir = args.output_dir.resolve()
    rag_dir = args.rag_dir.resolve()

    try:
        pdfs = _selected_pdfs(args, books_dir)
        if not pdfs:
            print(f"No PDF files found in {books_dir}")
            return 1

        config = _build_config(output_dir, force=args.force, verbose=not args.quiet)
        tracker = ProgressTracker(verbose=config.verbose, run_name="book_ocr")
        tracker.start()
        tracker.set_input_output(str(books_dir), str(output_dir))
        tracker.set_total(len(pdfs))

        client = OCRClient(api_key=config.api_key, max_retries=config.max_retries)
        processor = PDFProcessor(client, config, progress_tracker=tracker)
        rag_targets: list[Path] = []

        for pdf_path in pdfs:
            tracker.start_file(pdf_path.name)
            result = processor.process(pdf_path)
            if result.success:
                if result.skipped:
                    tracker.skip_file(pdf_path.name)
                else:
                    tracker.complete_file(pdf_path.name, success=True)
                if args.register_rag and result.output_path:
                    rag_targets.append(_register_for_rag(result.output_path, rag_dir))
            else:
                tracker.complete_file(pdf_path.name, success=False)
                tracker.error(f"{pdf_path.name}: {result.error}")

        tracker.print_summary()
        if rag_targets:
            print("\nRegistered for RAG:")
            for target in rag_targets:
                print(f"  {target}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
