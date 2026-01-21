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
import json
import sys
from pathlib import Path
from typing import Any

from src.models.sanitized import SanitizedTranscript, SanitizedTurn
from src.utils.logging_utils import setup_logging

# Noise patterns to filter out
NOISE_PATTERNS = frozenset(["[noise]", "<unk>"])

# Role mapping from raw format to sanitized format
ROLE_MAP = {
    "agent": "assistant",
    "caller": "user",
}


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


def is_noise(text: str) -> bool:
    """Check if a transcript text is noise or empty."""
    stripped = text.strip()
    return stripped == "" or stripped in NOISE_PATTERNS


def sanitize_transcript(raw_turns: list[dict[str, Any]], conversation_id: str) -> SanitizedTranscript:
    """
    Sanitize a raw transcript by filtering noise, mapping roles, and merging consecutive same-speaker turns.

    Args:
        raw_turns: List of raw turn objects from input JSON
        conversation_id: ID for this conversation

    Returns:
        SanitizedTranscript with cleaned and merged turns
    """
    # Sort by index to ensure correct order
    sorted_turns = sorted(raw_turns, key=lambda t: t.get("index", 0))

    # Filter noise and map to intermediate format
    filtered_turns: list[dict[str, Any]] = []
    for turn in sorted_turns:
        text = turn.get("human_transcript", "")
        if is_noise(text):
            continue

        raw_role = turn.get("speaker_role", "")
        role = ROLE_MAP.get(raw_role)
        if role is None:
            # Skip unknown roles
            continue

        filtered_turns.append({
            "role": role,
            "text": text,
            "timestamp": turn.get("start_timestamp_ms", 0),
        })

    # Merge consecutive same-speaker turns
    merged_turns: list[SanitizedTurn] = []
    turn_count = 0

    for turn in filtered_turns:
        if merged_turns and merged_turns[-1].role == turn["role"]:
            # Merge with previous turn - append text with space separator
            prev = merged_turns[-1]
            merged_turns[-1] = SanitizedTurn(
                role=prev.role,
                text=f"{prev.text} {turn['text']}",
                turnCount=prev.turnCount,
                timestamp=prev.timestamp,  # Keep original timestamp
            )
        else:
            # New speaker - create new turn
            turn_count += 1
            merged_turns.append(SanitizedTurn(
                role=turn["role"],
                text=turn["text"],
                turnCount=turn_count,
                timestamp=turn["timestamp"],
            ))

    return SanitizedTranscript(
        conversation_id=conversation_id,
        turns=merged_turns,
    )


def process_file(input_path: Path, output_dir: Path, logger) -> bool:
    """
    Process a single raw transcript file.

    Args:
        input_path: Path to raw JSON file
        output_dir: Directory to write sanitized output
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            raw_turns = json.load(f)

        # Use filename (without extension) as conversation ID
        conversation_id = input_path.stem

        sanitized = sanitize_transcript(raw_turns, conversation_id)

        # Write output
        output_path = output_dir / f"{conversation_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(sanitized.model_dump_json(indent=2))

        logger.debug(f"Processed {input_path.name}: {len(raw_turns)} raw turns -> {len(sanitized.turns)} sanitized turns")
        return True

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {input_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error processing {input_path}: {e}")
        return False


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    logger = setup_logging(verbose=args.verbose, name="sanitize")

    input_path: Path = args.input
    output_dir: Path = args.output

    # Validate input
    if not input_path.exists():
        logger.error(f"Input path does not exist: {input_path}")
        return 1

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect input files
    if input_path.is_file():
        input_files = [input_path]
    else:
        input_files = sorted(input_path.glob("*.json"))

    if not input_files:
        logger.error(f"No JSON files found in {input_path}")
        return 1

    logger.info(f"Processing {len(input_files)} file(s) from {input_path}")

    # Process files
    success_count = 0
    error_count = 0

    for file_path in input_files:
        if process_file(file_path, output_dir, logger):
            success_count += 1
        else:
            error_count += 1

    logger.info(f"Completed: {success_count} succeeded, {error_count} failed")
    logger.info(f"Output written to {output_dir}")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
