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
        # Update step status to running
        step = session.steps[step_id]
        step.status = StepStatus.RUNNING
        step.progress_percent = 0.0
        step.error_message = None

        await ws_manager.broadcast_status(session.session_id, step_id, StepStatus.RUNNING.value)

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

        except Exception as e:
            # Mark as failed
            error_msg = str(e)
            step.status = StepStatus.FAILED
            step.error_message = error_msg
            await ws_manager.broadcast_status(session.session_id, step_id, StepStatus.FAILED.value)
            await ws_manager.broadcast_error(session.session_id, step_id, error_msg)
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
        # Parse config
        step_config = Step2Config(**(config or {}))

        input_dir = temp_manager.get_step_input_dir(session, 2)
        output_dir = temp_manager.get_step_output_dir(session, 2)

        # Set environment variables
        env = os.environ.copy()
        env["REWRITE_THRESHOLD"] = str(step_config.rewrite_threshold)

        cmd = [
            "python",
            str(settings.scripts_dir / "tag_transcripts.py"),
            "--input", str(input_dir),
            "--output", str(output_dir),
            "--provider", step_config.llm_provider,
            "--model", step_config.model,
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
        # Parse config
        step_config = Step4Config(**(config or {}))

        input_file = temp_manager.get_step_output_dir(session, 3) / "train.json"
        output_dir = temp_manager.get_step_output_dir(session, 4)

        # Note: This is a placeholder - actual LlamaFactory integration would go here
        # For now, we'll create a simple training script call
        cmd = [
            "python",
            str(settings.scripts_dir / "train_lora.py"),
            "--data", str(input_file),
            "--output", str(output_dir),
            "--model", step_config.base_model,
            "--epochs", str(step_config.epochs),
            "--batch-size", str(step_config.batch_size),
            "--learning-rate", str(step_config.learning_rate),
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

        while True:
            line_bytes = await process.stdout.readline()
            if not line_bytes:
                break

            line = line_bytes.decode("utf-8").strip()
            if line:
                # Broadcast log
                await ws_manager.broadcast_log(session_id, step_id, line)
                yield line

        # Wait for process to complete
        await process.wait()

        if process.returncode != 0:
            raise RuntimeError(f"Step {step_id} failed with exit code {process.returncode}")

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
