#!/usr/bin/env python3
"""
Step 1: Sanitization - Clean and normalize raw transcripts.

Usage:
    python scripts/sanitize_transcripts.py --input data/raw/ --output data/Step-1-Sanitization/output/

Operations:
    1. Filter noise entries ([noise], <unk>, empty strings)
    2. Map roles: agent -> assistant, caller -> user
    3. Join consecutive same-speaker turns
    4. Assign sequential turnCount
"""

import argparse
import sys
from pathlib import Path


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Step 1: Clean and normalize raw transcripts",
    )

    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Input path (directory of JSON files or single JSON file)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Output directory for sanitized transcripts",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    # TODO: Implement sanitization logic
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print("Sanitization not yet implemented.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
