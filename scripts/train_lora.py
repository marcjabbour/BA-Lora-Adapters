#!/usr/bin/env python3
"""
Step 4: Train LoRA adapters using LlamaFactory

This script wraps llamafactory-cli to provide:
- Validation of config files
- Environment setup (DATASET_DIR)
- Consistent logging with Steps 1-3
- Error handling

The actual training is performed by LlamaFactory's implementation.
"""

import argparse
import sys
import subprocess
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging_utils import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="Train LoRA adapters with LlamaFactory"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/llamafactory/train_lora.yaml",
        help="Path to LlamaFactory training config YAML",
    )
    parser.add_argument(
        "--dataset-info",
        type=str,
        default="configs/llamafactory/dataset_info.json",
        help="Path to dataset_info.json",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()
    logger = setup_logging(verbose=args.verbose)

    # Validate files exist
    config_path = Path(args.config).resolve()
    dataset_info_path = Path(args.dataset_info).resolve()

    if not config_path.exists():
        logger.error(f"Training config not found: {config_path}")
        sys.exit(1)

    if not dataset_info_path.exists():
        logger.error(f"Dataset info not found: {dataset_info_path}")
        sys.exit(1)

    logger.info(f"Using training config: {config_path}")
    logger.info(f"Using dataset info: {dataset_info_path}")

    # Get project root directory (parent of scripts/)
    project_root = Path(__file__).parent.parent

    # Set environment variable for LlamaFactory to find dataset_info.json
    # LlamaFactory looks for dataset_info.json in DATASET_DIR
    os.environ["DATASET_DIR"] = str(dataset_info_path.parent)

    # Run llamafactory-cli train (LlamaFactory does all the heavy lifting)
    cmd = [
        "llamafactory-cli",
        "train",
        str(config_path),
    ]

    logger.info(f"Running: {' '.join(cmd)}")
    logger.info(f"Dataset directory: {dataset_info_path.parent}")
    logger.info(f"Working directory: {project_root}")
    logger.info("Training started (this may take several hours on CPU)...")
    logger.info("LlamaFactory will handle model download, data loading, and training")

    try:
        # Pass through to llamafactory-cli with environment variable, showing output in real-time
        # Run from project root so relative paths in config resolve correctly
        env = os.environ.copy()
        env["DATASET_DIR"] = str(dataset_info_path.parent)
        result = subprocess.run(cmd, check=True, env=env, cwd=str(project_root))

        logger.info("✓ Training completed successfully!")

    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Training failed with error code {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        logger.error("✗ llamafactory-cli not found. Install with: pip install llamafactory")
        sys.exit(1)


if __name__ == "__main__":
    main()
