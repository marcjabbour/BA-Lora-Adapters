#!/usr/bin/env python3
"""
Test trained LoRA adapter with sample conversations
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging_utils import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="Test trained LoRA adapter"
    )
    parser.add_argument(
        "--adapter-path",
        type=str,
        required=True,
        help="Path to trained adapter directory",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen2-1.5B-Instruct",
        help="Base model name",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="hi i would like to check my account balance",
        help="Test prompt (user message)",
    )

    args = parser.parse_args()
    logger = setup_logging(verbose=True)

    # Use llamafactory-cli chat for inference
    import subprocess

    logger.info(f"Loading adapter from: {args.adapter_path}")
    logger.info(f"Test prompt: {args.prompt}")

    # Create temporary chat config
    import tempfile
    import yaml

    chat_config = {
        "model_name_or_path": args.model,
        "adapter_name_or_path": args.adapter_path,
        "template": "qwen",
        "finetuning_type": "lora",
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(chat_config, f)
        config_path = f.name

    try:
        # Run inference
        cmd = [
            "llamafactory-cli",
            "chat",
            config_path,
        ]

        logger.info("Starting interactive chat...")
        logger.info("(Type your message and press Enter)")

        subprocess.run(cmd, check=True)

    finally:
        Path(config_path).unlink()


if __name__ == "__main__":
    main()
