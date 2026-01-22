import pytest
from pathlib import Path
import json


class TestDatasetRegistration:
    """Test LlamaFactory dataset configuration"""

    def test_dataset_info_exists(self):
        """Verify dataset_info.json exists"""
        dataset_info = Path("configs/llamafactory/dataset_info.json")
        assert dataset_info.exists()

    def test_dataset_info_valid_json(self):
        """Verify dataset_info.json is valid JSON"""
        dataset_info = Path("configs/llamafactory/dataset_info.json")
        with open(dataset_info) as f:
            data = json.load(f)

        assert "hvnb_transcripts" in data
        assert data["hvnb_transcripts"]["formatting"] == "sharegpt"

    def test_sharegpt_dataset_exists(self):
        """Verify ShareGPT dataset file exists"""
        dataset = Path("data/Step-3-Exporting/output/sharegpt_dataset.json")
        assert dataset.exists()

    def test_sharegpt_dataset_format(self):
        """Verify ShareGPT dataset has correct structure"""
        dataset = Path("data/Step-3-Exporting/output/sharegpt_dataset.json")
        with open(dataset) as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) > 0

        # Check first record structure
        record = data[0]
        assert "conversations" in record
        assert isinstance(record["conversations"], list)

        # Check message structure
        if len(record["conversations"]) > 0:
            msg = record["conversations"][0]
            assert "from" in msg
            assert "value" in msg
            assert msg["from"] in ["human", "gpt"]


class TestTrainingConfig:
    """Test training configuration"""

    def test_train_config_exists(self):
        """Verify training config YAML exists"""
        config = Path("configs/llamafactory/train_lora.yaml")
        assert config.exists()

    def test_train_config_valid_yaml(self):
        """Verify training config is valid YAML"""
        import yaml

        config = Path("configs/llamafactory/train_lora.yaml")
        with open(config) as f:
            data = yaml.safe_load(f)

        # Check required fields
        assert data["stage"] == "sft"
        assert data["finetuning_type"] == "lora"
        assert data["dataset"] == "hvnb_transcripts"
        assert data["do_train"] is True
