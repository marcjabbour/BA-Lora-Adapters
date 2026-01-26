"""Pipeline step execution via subprocess."""

import asyncio
import os
import re
from pathlib import Path
from typing import AsyncGenerator, Optional

from app.config import settings
from app.core.websocket_manager import ws_manager
from app.models.state import SessionState, Step2Config, Step4Config, StepStatus
from app.services.temp_manager import temp_manager


class PipelineExecutor:
    """Executes pipeline steps via subprocess."""

    async def execute_step(
        self,
        session: SessionState,
        step_id: int,
        config: Optional[dict] = None
    ):
        """
        Execute a pipeline step.

        Args:
            session: Session state
            step_id: Step number (1-4)
            config: Optional step configuration
        """
        print(f"⚙️  [Step {step_id}] Starting execution for session {session.session_id}")

        # Update step status to running
        step = session.steps[step_id]
        step.status = StepStatus.RUNNING
        step.progress_percent = 0.0
        step.error_message = None

        await ws_manager.broadcast_status(session.session_id, step_id, StepStatus.RUNNING.value)
        print(f"📡 [Step {step_id}] Broadcasted RUNNING status")

        try:
            # Execute the appropriate step
            if step_id == 1:
                await self._execute_step_1(session)
            elif step_id == 2:
                await self._execute_step_2(session, config)
            elif step_id == 3:
                await self._execute_step_3(session)
            elif step_id == 4:
                await self._execute_step_4(session, config)
            else:
                raise ValueError(f"Step {step_id} not implemented")

            # Mark as completed
            step.status = StepStatus.COMPLETED
            step.progress_percent = 100.0
            await ws_manager.broadcast_status(session.session_id, step_id, StepStatus.COMPLETED.value)
            await ws_manager.broadcast_progress(session.session_id, step_id, 100.0, "Completed!")
            print(f"✅ [Step {step_id}] Completed successfully")

        except Exception as e:
            # Mark as failed
            error_msg = str(e)
            step.status = StepStatus.FAILED
            step.error_message = error_msg
            await ws_manager.broadcast_status(session.session_id, step_id, StepStatus.FAILED.value)
            await ws_manager.broadcast_error(session.session_id, step_id, error_msg)
            print(f"❌ [Step {step_id}] Failed with error: {error_msg}")
            raise

    async def _execute_step_1(self, session: SessionState):
        """Execute Step 1: Sanitization."""
        input_dir = temp_manager.get_step_input_dir(session, 1)
        output_dir = temp_manager.get_step_output_dir(session, 1)

        cmd = [
            "python",
            str(settings.scripts_dir / "sanitize_transcripts.py"),
            "--input", str(input_dir),
            "--output", str(output_dir),
            "--verbose"
        ]

        async for line in self._run_subprocess(cmd, session.session_id, 1):
            # Parse progress from output
            progress = self._parse_progress_generic(line)
            if progress is not None:
                session.steps[1].progress_percent = progress
                await ws_manager.broadcast_progress(session.session_id, 1, progress, line)

    async def _execute_step_2(self, session: SessionState, config: Optional[dict]):
        """Execute Step 2: LLM Tagging."""
        # Check if API key is set
        if not settings.openai_api_key:
            raise ValueError(
                "OpenAI API key not set. Please add OPENAI_API_KEY to backend/.env file."
            )

        # Parse config
        step_config = Step2Config(**(config or {}))

        input_dir = temp_manager.get_step_input_dir(session, 2)
        output_dir = temp_manager.get_step_output_dir(session, 2)

        # Set environment variables
        env = os.environ.copy()
        env["REWRITE_THRESHOLD"] = str(step_config.rewrite_threshold)
        env["OPENAI_API_KEY"] = settings.openai_api_key

        # Use absolute paths to config and prompt files
        config_path = settings.project_root / "configs" / "llm_config.yaml"
        prompt_path = settings.project_root / "prompts" / "tagging" / "tagging_prompt.txt"

        cmd = [
            "python",
            str(settings.scripts_dir / "tag_transcripts.py"),
            "--input", str(input_dir),
            "--output", str(output_dir),
            "--provider", step_config.llm_provider,
            "--model", step_config.model,
            "--config", str(config_path),
            "--prompt", str(prompt_path),
            "--verbose"
        ]

        async for line in self._run_subprocess(cmd, session.session_id, 2, env):
            # Parse progress (look for "Processing file X/Y")
            match = re.search(r"Processing.*?(\d+)/(\d+)", line)
            if match:
                current, total = int(match.group(1)), int(match.group(2))
                progress = (current / total) * 100
                session.steps[2].progress_percent = progress
                await ws_manager.broadcast_progress(session.session_id, 2, progress, line)

    async def _execute_step_3(self, session: SessionState):
        """Execute Step 3: Exporting to ShareGPT."""
        input_dir = temp_manager.get_step_input_dir(session, 3)
        output_dir = temp_manager.get_step_output_dir(session, 3)

        cmd = [
            "python",
            str(settings.scripts_dir / "export_to_sharegpt.py"),
            "--input", str(input_dir),
            "--output", str(output_dir / "train.json"),
            "--verbose"
        ]

        async for line in self._run_subprocess(cmd, session.session_id, 3):
            # Parse progress
            progress = self._parse_progress_generic(line)
            if progress is not None:
                session.steps[3].progress_percent = progress
                await ws_manager.broadcast_progress(session.session_id, 3, progress, line)

    async def _execute_step_4(self, session: SessionState, config: Optional[dict]):
        """Execute Step 4: Training with LlamaFactory."""
        import yaml
        import shutil
        import json

        # Parse config
        step_config = Step4Config(**(config or {}))

        input_file = temp_manager.get_step_output_dir(session, 3) / "train.json"
        output_dir = temp_manager.get_step_output_dir(session, 4)

        # Create session-specific config directory
        session_config_dir = session.temp_dir / "configs"
        session_config_dir.mkdir(exist_ok=True)

        # Copy train.json to session config dir (as sharegpt_dataset.json)
        dataset_file = session_config_dir / "sharegpt_dataset.json"
        shutil.copy(input_file, dataset_file)

        # Create dataset_info.json in session config dir
        dataset_info = {
            "hvnb_transcripts": {
                "file_name": "sharegpt_dataset.json",
                "formatting": "sharegpt",
                "columns": {
                    "messages": "conversations"
                },
                "tags": {
                    "role_tag": "from",
                    "content_tag": "value",
                    "user_tag": "human",
                    "assistant_tag": "gpt"
                }
            }
        }
        dataset_info_file = session_config_dir / "dataset_info.json"
        with open(dataset_info_file, "w") as f:
            json.dump(dataset_info, f, indent=2)

        # Create session-specific training config
        train_config = {
            "model_name_or_path": step_config.base_model,
            "stage": "sft",
            "do_train": True,
            "finetuning_type": "lora",
            "lora_target": "all",
            "lora_rank": 8,
            "lora_alpha": 16,
            "dataset": "hvnb_transcripts",
            "dataset_dir": str(session_config_dir),
            "template": "qwen" if "qwen" in step_config.base_model.lower() else "default",
            "cutoff_len": 2048,
            "max_samples": 500,
            "overwrite_cache": True,
            "preprocessing_num_workers": 4,
            "output_dir": str(output_dir),
            "logging_steps": 10,
            "save_steps": 100,
            "plot_loss": True,
            "overwrite_output_dir": True,
            "per_device_train_batch_size": step_config.batch_size,
            "gradient_accumulation_steps": 4,
            "learning_rate": step_config.learning_rate,
            "num_train_epochs": float(step_config.epochs),
            "lr_scheduler_type": "cosine",
            "warmup_ratio": 0.1,
            "bf16": False,
            "val_size": 0.0,
            "eval_strategy": "no"
        }

        train_config_file = session_config_dir / "train_lora.yaml"
        with open(train_config_file, "w") as f:
            yaml.dump(train_config, f, default_flow_style=False)

        # Run training script
        cmd = [
            "python",
            str(settings.scripts_dir / "train_lora.py"),
            "--config", str(train_config_file),
            "--dataset-info", str(dataset_info_file),
            "--verbose"
        ]

        async for line in self._run_subprocess(cmd, session.session_id, 4):
            # Parse training progress (look for epoch/step info)
            # Example: "[Epoch 1/3] [Step 100/303] loss: 1.234"
            match = re.search(r"Epoch (\d+)/(\d+).*?Step (\d+)/(\d+)", line)
            if match:
                epoch, total_epochs = int(match.group(1)), int(match.group(2))
                step, total_steps = int(match.group(3)), int(match.group(4))
                progress = ((epoch - 1) * total_steps + step) / (total_epochs * total_steps) * 100
                session.steps[4].progress_percent = progress
                await ws_manager.broadcast_progress(session.session_id, 4, progress, line)

    async def _run_subprocess(
        self,
        cmd: list[str],
        session_id: str,
        step_id: int,
        env: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Run subprocess and yield output lines.

        Args:
            cmd: Command to run
            session_id: Session identifier
            step_id: Step number
            env: Optional environment variables

        Yields:
            Output lines from the subprocess
        """
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env or os.environ.copy()
        )

        output_lines = []
        while True:
            line_bytes = await process.stdout.readline()
            if not line_bytes:
                break

            line = line_bytes.decode("utf-8").strip()
            if line:
                output_lines.append(line)
                # Print to console for debugging
                print(f"[Step {step_id}] {line}")
                # Broadcast log
                await ws_manager.broadcast_log(session_id, step_id, line)
                yield line

        # Wait for process to complete
        await process.wait()

        if process.returncode != 0:
            # Show last few lines of output for debugging
            error_context = "\n".join(output_lines[-10:]) if output_lines else "No output"
            print(f"❌ [Step {step_id}] Process failed. Last output:\n{error_context}")
            raise RuntimeError(
                f"Step {step_id} failed with exit code {process.returncode}. "
                f"Last output: {output_lines[-1] if output_lines else 'No output'}"
            )

    def _parse_progress_generic(self, line: str) -> Optional[float]:
        """
        Try to parse progress percentage from a line.

        Args:
            line: Output line

        Returns:
            Progress percentage if found, None otherwise
        """
        # Look for patterns like "50%" or "Progress: 50%"
        match = re.search(r"(\d+)%", line)
        if match:
            return float(match.group(1))

        return None


# Global instance
pipeline_executor = PipelineExecutor()
