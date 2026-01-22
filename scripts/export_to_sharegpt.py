#!/usr/bin/env python3
"""
Step 3: Exporting - Convert tagged transcripts to ShareGPT format for SFT.

Usage:
    python scripts/export_to_sharegpt.py \
        --input data/Step-2-Tagging/output/ \
        --output data/Step-3-Exporting/output/

Algorithm:
    1. Initialize empty records and history lists
    2. For each turn:
       - If user: add to history as {"from": "human", "value": text}
       - If assistant:
         - Skip if no human message yet in history
         - If rewrite_needed=true: add rewrite to history, skip record creation
           (last gpt message is the SFT target; we don't train on poor responses)
         - Otherwise: create ShareGPT record with history + [assistant message]
         - Add assistant message to history for future records
    3. Output as JSON/JSONL
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.tagged import TaggedTranscript, TaggedTurn
from src.models.sharegpt import ShareGPTMessage, ShareGPTRecord
from src.utils.logging_utils import setup_logging


def convert_transcript_to_sharegpt(
    transcript: TaggedTranscript,
    logger,
) -> list[ShareGPTRecord]:
    """
    Convert a tagged transcript to ShareGPT format.

    Creates one record per assistant turn with cumulative conversation history.

    Args:
        transcript: The tagged transcript to convert
        logger: Logger instance

    Returns:
        List of ShareGPT records (one per assistant turn)
    """
    records: list[ShareGPTRecord] = []
    history: list[ShareGPTMessage] = []
    assistant_turn_index = 0

    for turn in transcript.turns:
        if turn.role == "user":
            # Add user message to history
            history.append(ShareGPTMessage(from_="human", value=turn.text))  # type: ignore[call-arg]

        elif turn.role == "assistant":
            assistant_turn_index += 1

            # ShareGPT format requires the first message to be from "human".
            # If no human message in history yet, prepend an empty human message.
            has_human_in_history = any(msg.from_ == "human" for msg in history)
            if not has_human_in_history:
                empty_human = ShareGPTMessage(from_="human", value="")  # type: ignore[call-arg]
                history.insert(0, empty_human)
                logger.debug(
                    f"Prepending empty human message in {transcript.conversation_id}: "
                    f"assistant turn {assistant_turn_index} is first"
                )

            # Check if this turn has rewrite_needed=true
            # In ShareGPT SFT, the last gpt message is the supervised target.
            # We don't want to train on poor-quality responses, so skip creating
            # a record. But we still add the rewrite to history for future turns.
            if turn.tags and turn.tags.rewrite_needed:
                # Use rewrite in history if available, else fallback to original
                text_for_history = turn.tags.rewrite if turn.tags.rewrite else turn.text
                history.append(ShareGPTMessage(from_="gpt", value=text_for_history))  # type: ignore[call-arg]
                logger.debug(
                    f"Skipping assistant turn {assistant_turn_index} in "
                    f"{transcript.conversation_id}: rewrite_needed=true (not used as training target)"
                )
                continue

            # Normal case: use original text, create a training record
            assistant_message = ShareGPTMessage(from_="gpt", value=turn.text)  # type: ignore[call-arg]

            # Build the conversation: history + current assistant message
            conversations = [msg.model_copy() for msg in history]
            conversations.append(assistant_message)

            # Create the ShareGPT record
            record = ShareGPTRecord(conversations=conversations)
            records.append(record)

            # Add to history for future records
            history.append(assistant_message)

    return records


def process_file(
    input_path: Path,
    logger,
) -> tuple[list[ShareGPTRecord], int, int]:
    """
    Process a single tagged transcript file.

    Args:
        input_path: Path to the tagged transcript JSON file
        logger: Logger instance

    Returns:
        Tuple of (records, success_count, error_count)
    """
    try:
        # Load tagged transcript
        with open(input_path) as f:
            data = json.load(f)
        transcript = TaggedTranscript(**data)

        logger.debug(f"Processing {transcript.conversation_id} ({len(transcript.turns)} turns)")

        # Convert to ShareGPT format
        records = convert_transcript_to_sharegpt(transcript, logger)

        logger.debug(f"Generated {len(records)} ShareGPT records from {transcript.conversation_id}")

        return records, 1, 0

    except Exception as e:
        logger.error(f"Failed to process {input_path.name}: {e}")
        return [], 0, 1


def write_output_json(
    records: list[ShareGPTRecord],
    output_path: Path,
    logger,
) -> None:
    """Write records as a single JSON array."""
    # Serialize with proper aliases (_meta, from)
    serialized = [
        json.loads(record.model_dump_json(by_alias=True))
        for record in records
    ]

    with open(output_path, "w") as f:
        json.dump(serialized, f, indent=2)

    logger.info(f"Wrote {len(records)} records to {output_path}")


def write_output_jsonl(
    records: list[ShareGPTRecord],
    output_path: Path,
    logger,
) -> None:
    """Write records as JSONL (one record per line)."""
    with open(output_path, "w") as f:
        for record in records:
            f.write(record.model_dump_json(by_alias=True) + "\n")

    logger.info(f"Wrote {len(records)} records to {output_path}")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Step 3: Export tagged transcripts to ShareGPT format",
    )

    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Input directory with tagged transcripts",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Output directory for ShareGPT files",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "jsonl"],
        default="json",
        help="Output format (default: json)",
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

    logger = setup_logging(verbose=args.verbose, name="exporting")

    # Validate input directory
    if not args.input.exists():
        logger.error(f"Input directory not found: {args.input}")
        return 1

    # Collect input files
    if args.input.is_file():
        input_files = [args.input]
    else:
        input_files = sorted(args.input.glob("*.json"))

    if not input_files:
        logger.error(f"No JSON files found in {args.input}")
        return 1

    logger.info(f"Processing {len(input_files)} files")

    # Process all files and collect records
    all_records: list[ShareGPTRecord] = []
    total_success = 0
    total_errors = 0

    for input_path in input_files:
        records, success, errors = process_file(input_path, logger)
        all_records.extend(records)
        total_success += success
        total_errors += errors

    if not all_records:
        logger.error("No records generated")
        return 1

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Write output
    if args.format == "json":
        output_path = args.output / "sharegpt_dataset.json"
        write_output_json(all_records, output_path, logger)
    else:
        output_path = args.output / "sharegpt_dataset.jsonl"
        write_output_jsonl(all_records, output_path, logger)

    # Report results
    logger.info(
        f"Completed: {total_success} files processed, {total_errors} errors, "
        f"{len(all_records)} total training records"
    )

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
