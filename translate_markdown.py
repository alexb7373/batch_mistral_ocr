#!/usr/bin/env python3
"""Translate markdown to English with Mistral while preserving structure."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mistralai.client import Mistral

from src.config.settings import load_api_key
from src.translation.markdown_translator import translate_markdown_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate markdown to English while preserving Markdown and LaTeX."
    )
    parser.add_argument("input", type=Path, help="Input markdown file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output markdown file. Defaults to <input>.en.md",
    )
    parser.add_argument(
        "--model",
        default="mistral-small-latest",
        help="Mistral chat model to use for translation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve() if args.output else input_path.with_suffix(".en.md")

    try:
        api_key = load_api_key()
        client = Mistral(api_key=api_key)
        translate_markdown_file(input_path, output_path, client, model=args.model)
        print(output_path)
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

