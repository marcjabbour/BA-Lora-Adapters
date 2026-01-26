"""File upload, download, and preview operations."""

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from fastapi import UploadFile

from app.models.state import SessionState
from app.services.temp_manager import temp_manager


class FileHandler:
    """Handles file operations for the pipeline."""

    async def upload_files(
        self,
        session: SessionState,
        files: List[UploadFile],
        target_step: int = 1
    ) -> int:
        """
        Upload files to session directory for a specific step.

        Args:
            session: Session state
            files: List of uploaded files
            target_step: Target step number (default: 1 for raw files)

        Returns:
            Number of files uploaded
        """
        # Determine target directory based on step
        if target_step == 1:
            target_dir = session.temp_dir / "raw"
        else:
            # Upload to the input directory of the target step
            # which is the output directory of the previous step
            target_dir = temp_manager.get_step_input_dir(session, target_step)

        target_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for file in files:
            # Save file
            file_path = target_dir / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            count += 1

        return count

    async def preview_step_output(
        self,
        session: SessionState,
        step_id: int,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Get preview of step output files.

        Args:
            session: Session state
            step_id: Step number
            limit: Maximum number of files to preview

        Returns:
            Dictionary with preview data
        """
        output_dir = temp_manager.get_step_output_dir(session, step_id)

        if not output_dir.exists():
            return {"files": [], "total_files": 0}

        # Get all JSON files
        json_files = list(output_dir.glob("*.json"))
        total_files = len(json_files)

        # Load first N files
        previews = []
        for file_path in json_files[:limit]:
            try:
                with open(file_path, "r") as f:
                    content = json.load(f)
                    previews.append({
                        "filename": file_path.name,
                        "content": content
                    })
            except Exception as e:
                previews.append({
                    "filename": file_path.name,
                    "error": str(e)
                })

        return {
            "step_id": step_id,
            "files": previews,
            "total_files": total_files
        }

    async def download_adapter(
        self,
        session: SessionState
    ) -> Path:
        """
        Create a zip file of the trained adapter.

        Args:
            session: Session state

        Returns:
            Path to the zip file
        """
        output_dir = temp_manager.get_step_output_dir(session, 4)
        zip_path = session.temp_dir / "adapter.zip"

        # Create zip file
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in output_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(output_dir)
                    zipf.write(file_path, arcname)

        return zip_path

    async def download_step_file(
        self,
        session: SessionState,
        step_id: int,
        filename: str
    ) -> Path:
        """
        Get path to a specific step output file.

        Args:
            session: Session state
            step_id: Step number
            filename: Filename to download

        Returns:
            Path to the file
        """
        output_dir = temp_manager.get_step_output_dir(session, step_id)
        file_path = output_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filename}")

        return file_path

    def get_step_output_files(
        self,
        session: SessionState,
        step_id: int
    ) -> List[str]:
        """
        Get list of output files for a step.

        Args:
            session: Session state
            step_id: Step number

        Returns:
            List of filenames
        """
        output_dir = temp_manager.get_step_output_dir(session, step_id)

        if not output_dir.exists():
            return []

        files = [f.name for f in output_dir.iterdir() if f.is_file()]
        return sorted(files)


# Global instance
file_handler = FileHandler()
