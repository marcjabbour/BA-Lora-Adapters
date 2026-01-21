#!/usr/bin/env python3
"""
Step 2: Tagging - LLM-based quality assessment and rewriting.

Usage:
    python scripts/tag_transcripts.py \
        --input data/Step-1-Sanitization/output/ \
        --output data/Step-2-Tagging/output/ \
        --provider openai

Operations:
    1. For each conversation, send to LLM for evaluation
    2. LLM returns per-turn scores, quality labels, issues
    3. Determine if rewrite needed (score < threshold)
    4. Generate rewrites for poor responses
    5. Create conversation-level summary
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from tqdm import tqdm

from src.llm.client import create_llm_client, LLMClient
from src.models.sanitized import SanitizedTranscript
from src.models.tagged import (
    TaggedTranscript,
    TaggedTurn,
    TurnTags,
    ConversationTags,
)
from src.utils.logging_utils import setup_logging

# Load environment variables
load_dotenv()

# Default paths
CONFIG_PATH = Path("configs/llm_config.yaml")
PROMPT_PATH = Path("prompts/tagging/tagging_prompt.txt")


def load_config(config_path: Path) -> dict:
    """Load LLM configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_prompt(prompt_path: Path) -> str:
    """Load the tagging prompt template."""
    with open(prompt_path) as f:
        return f.read()


def format_conversation_for_llm(transcript: SanitizedTranscript) -> str:
    """Format a sanitized transcript for LLM input."""
    lines = []
    for turn in transcript.turns:
        lines.append(f"[Turn {turn.turnCount} - {turn.role}] {turn.text}")
    return "\n".join(lines)


def extract_json_from_response(response: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try to find JSON in code blocks first
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # Try to parse the whole response as JSON
    # Find the first { and last } to extract JSON object
    start = response.find("{")
    end = response.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(response[start:end])

    raise ValueError("No valid JSON found in LLM response")


def tag_transcript(
    transcript: SanitizedTranscript,
    client: LLMClient,
    system_prompt: str,
    rewrite_threshold: int,
    temperature: float,
    max_tokens: int,
    logger,
) -> TaggedTranscript:
    """
    Tag a single transcript using the LLM.

    Args:
        transcript: The sanitized transcript to tag
        client: LLM client instance
        system_prompt: The tagging prompt
        rewrite_threshold: Score below which rewrites are needed
        temperature: LLM temperature setting
        max_tokens: Max tokens for LLM response
        logger: Logger instance

    Returns:
        Tagged transcript with evaluations and rewrites
    """
    # Format conversation for LLM
    user_prompt = format_conversation_for_llm(transcript)

    logger.debug(f"Sending conversation {transcript.conversation_id} to LLM")

    # Get LLM response
    response = client.complete(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Parse LLM response
    try:
        result = extract_json_from_response(response)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse LLM response for {transcript.conversation_id}: {e}")
        logger.debug(f"Raw response: {response[:500]}...")
        raise

    # Build turn evaluations map (turn_number -> evaluation)
    evaluations = {
        eval_data["turn_number"]: eval_data
        for eval_data in result.get("turn_evaluations", [])
    }

    # Build tagged turns
    tagged_turns = []
    for turn in transcript.turns:
        if turn.role == "user":
            # User turns don't get tags
            tagged_turns.append(
                TaggedTurn(
                    role=turn.role,
                    text=turn.text,
                )
            )
        else:
            # Assistant turns get tags from LLM evaluation
            eval_data = evaluations.get(turn.turnCount, {})
            turn_score = eval_data.get("turn_score", 5)

            # Determine if rewrite is needed based on threshold
            rewrite_needed = turn_score < rewrite_threshold
            rewrite = eval_data.get("rewrite") if rewrite_needed else None

            tags = TurnTags(
                turn_score=turn_score,
                quality_labels=eval_data.get("quality_labels", []),
                issues=eval_data.get("issues", []),
                rewrite_needed=rewrite_needed,
                rewrite=rewrite,
            )

            tagged_turns.append(
                TaggedTurn(
                    role=turn.role,
                    text=turn.text,
                    turnCount=turn.turnCount,
                    timestamp=turn.timestamp,
                    tags=tags,
                )
            )

    # Build conversation tags
    conv_tags_data = result.get("conversation_tags", {})
    conversation_tags = ConversationTags(
        call_type=conv_tags_data.get("call_type", "unknown"),
        overall_quality=conv_tags_data.get("overall_quality", "mixed"),
        summary=conv_tags_data.get("summary", []),
    )

    return TaggedTranscript(
        conversation_id=transcript.conversation_id,
        conversation_tags=conversation_tags,
        turns=tagged_turns,
    )


def process_file(
    input_path: Path,
    output_dir: Path,
    client: LLMClient,
    system_prompt: str,
    rewrite_threshold: int,
    temperature: float,
    max_tokens: int,
    logger,
) -> bool:
    """
    Process a single sanitized transcript file.

    Returns:
        True if successful, False otherwise
    """
    try:
        # Load sanitized transcript
        with open(input_path) as f:
            data = json.load(f)
        transcript = SanitizedTranscript(**data)

        logger.debug(f"Processing {transcript.conversation_id} ({len(transcript.turns)} turns)")

        # Tag the transcript
        tagged = tag_transcript(
            transcript=transcript,
            client=client,
            system_prompt=system_prompt,
            rewrite_threshold=rewrite_threshold,
            temperature=temperature,
            max_tokens=max_tokens,
            logger=logger,
        )

        # Write output
        output_path = output_dir / input_path.name
        with open(output_path, "w") as f:
            f.write(tagged.model_dump_json(indent=2))

        logger.debug(f"Wrote tagged transcript to {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to process {input_path.name}: {e}")
        return False


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Step 2: LLM-based quality assessment and rewriting",
    )

    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Input directory with sanitized transcripts",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Output directory for tagged transcripts",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "local"],
        default=None,
        help="LLM provider (default: from config)",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Model name (uses provider default if not specified)",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=CONFIG_PATH,
        help="Path to LLM config file",
    )
    parser.add_argument(
        "--prompt",
        "-p",
        type=Path,
        default=PROMPT_PATH,
        help="Path to tagging prompt file",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Limit number of files to process (for testing)",
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

    logger = setup_logging(verbose=args.verbose, name="tagging")

    # Validate input directory
    if not args.input.exists():
        logger.error(f"Input directory not found: {args.input}")
        return 1

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        logger.error(f"Config file not found: {args.config}")
        return 1

    # Load prompt
    try:
        system_prompt = load_prompt(args.prompt)
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {args.prompt}")
        return 1

    # Get provider settings
    provider = args.provider or config.get("provider", "openai")
    provider_config = config.get(provider, {})
    model = args.model or provider_config.get("model")
    base_url = provider_config.get("base_url") if provider == "local" else None

    # Get generation parameters
    temperature = config.get("temperature", 0.1)
    max_tokens = config.get("max_tokens", 4096)
    rewrite_threshold = config.get("rewrite_threshold", 5)

    # Create LLM client
    try:
        client = create_llm_client(
            provider=provider,
            model=model,
            base_url=base_url,
        )
        logger.info(f"Using LLM: {client.get_name()}")
    except (ValueError, ImportError) as e:
        logger.error(f"Failed to create LLM client: {e}")
        return 1

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Collect input files
    if args.input.is_file():
        input_files = [args.input]
    else:
        input_files = sorted(args.input.glob("*.json"))

    if not input_files:
        logger.error(f"No JSON files found in {args.input}")
        return 1

    # Apply limit if specified
    if args.limit:
        input_files = input_files[: args.limit]

    logger.info(f"Processing {len(input_files)} files")
    logger.info(f"Rewrite threshold: score < {rewrite_threshold}")

    # Process files
    success_count = 0
    error_count = 0

    for input_path in tqdm(input_files, desc="Tagging transcripts", disable=args.verbose):
        if process_file(
            input_path=input_path,
            output_dir=args.output,
            client=client,
            system_prompt=system_prompt,
            rewrite_threshold=rewrite_threshold,
            temperature=temperature,
            max_tokens=max_tokens,
            logger=logger,
        ):
            success_count += 1
        else:
            error_count += 1

    # Report results
    logger.info(f"Completed: {success_count} succeeded, {error_count} failed")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
