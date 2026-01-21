"""
Unit tests for Step 3: Exporting to ShareGPT format

Tests cover:
- ShareGPT format generation
- Cumulative history building
- Skipping turns with rewrite_needed=true (not used as training targets)
- Rewrite in history for subsequent records
- Skipping assistant-first turns
- JSON/JSONL serialization
"""

import json
import pytest
import logging

from src.models.tagged import (
    TaggedTranscript,
    TaggedTurn,
    TurnTags,
    ConversationTags,
)
from src.models.sharegpt import ShareGPTMessage, ShareGPTRecord, Metadata

# Import functions from the exporting script
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.export_to_sharegpt import convert_transcript_to_sharegpt


# Create a simple logger for tests
@pytest.fixture
def logger():
    return logging.getLogger("test_exporting")


def create_tagged_transcript(turns: list[dict]) -> TaggedTranscript:
    """Helper to create a TaggedTranscript from simplified turn data."""
    tagged_turns = []
    for turn_data in turns:
        if turn_data["role"] == "user":
            tagged_turns.append(TaggedTurn(role="user", text=turn_data["text"]))
        else:
            tags = None
            if "tags" in turn_data:
                tags = TurnTags(**turn_data["tags"])
            tagged_turns.append(
                TaggedTurn(
                    role="assistant",
                    text=turn_data["text"],
                    turnCount=turn_data.get("turnCount"),
                    timestamp=turn_data.get("timestamp"),
                    tags=tags,
                )
            )

    return TaggedTranscript(
        conversation_id="test123",
        conversation_tags=ConversationTags(
            call_type="test",
            overall_quality="good",
            summary=["Test conversation"],
        ),
        turns=tagged_turns,
    )


class TestConvertTranscriptToShareGPT:
    """Tests for convert_transcript_to_sharegpt function."""

    def test_basic_conversation(self, logger):
        """Test basic user-assistant conversation."""
        transcript = create_tagged_transcript([
            {"role": "assistant", "text": "Hello, how can I help?", "turnCount": 1, "tags": {
                "turn_score": 8, "quality_labels": ["polite"], "issues": [], "rewrite_needed": False
            }},
            {"role": "user", "text": "I need help with my account"},
            {"role": "assistant", "text": "I'd be happy to help with your account.", "turnCount": 3, "tags": {
                "turn_score": 9, "quality_labels": ["helpful"], "issues": [], "rewrite_needed": False
            }},
        ])

        records = convert_transcript_to_sharegpt(transcript, logger)

        # First assistant turn is skipped (no human yet)
        # Second assistant turn creates a record
        assert len(records) == 1

        record = records[0]
        # Should have: assistant greeting (from history) + user message + assistant response
        assert len(record.conversations) == 3
        assert record.conversations[0].from_ == "gpt"
        assert record.conversations[1].from_ == "human"
        assert record.conversations[2].from_ == "gpt"
        assert record.meta.assistant_turn_index == 2
        assert record.meta.used_rewrite is False

    def test_rewrite_needed_turn_is_skipped(self, logger):
        """Test that turn with rewrite_needed=true is skipped (no record created)."""
        transcript = create_tagged_transcript([
            {"role": "user", "text": "Hi"},
            {"role": "assistant", "text": "what do you want", "turnCount": 2, "tags": {
                "turn_score": 3, "quality_labels": [], "issues": ["abrupt"],
                "rewrite_needed": True, "rewrite": "Hello! How can I assist you today?"
            }},
        ])

        records = convert_transcript_to_sharegpt(transcript, logger)

        # No record should be created for rewrite_needed turn
        assert len(records) == 0

    def test_original_used_when_rewrite_not_needed(self, logger):
        """Test that original text is used when rewrite_needed=false."""
        transcript = create_tagged_transcript([
            {"role": "user", "text": "Hi"},
            {"role": "assistant", "text": "Hello, how can I help?", "turnCount": 2, "tags": {
                "turn_score": 8, "quality_labels": ["polite"], "issues": [], "rewrite_needed": False
            }},
        ])

        records = convert_transcript_to_sharegpt(transcript, logger)

        assert len(records) == 1
        assert records[0].conversations[1].value == "Hello, how can I help?"
        assert records[0].meta.used_rewrite is False

    def test_rewrite_needed_skipped_even_when_rewrite_missing(self, logger):
        """Test that turn is skipped when rewrite_needed=true even if rewrite is None."""
        transcript = create_tagged_transcript([
            {"role": "user", "text": "Hi"},
            {"role": "assistant", "text": "okay", "turnCount": 2, "tags": {
                "turn_score": 4, "quality_labels": [], "issues": ["abrupt"],
                "rewrite_needed": True, "rewrite": None
            }},
        ])

        records = convert_transcript_to_sharegpt(transcript, logger)

        # Still skipped - rewrite_needed=true means it's not suitable as training target
        assert len(records) == 0

    def test_rewrite_in_history_for_subsequent_turns(self, logger):
        """Test that rewrite appears in history for turns following a skipped turn."""
        transcript = create_tagged_transcript([
            {"role": "user", "text": "Hi"},
            {"role": "assistant", "text": "what", "turnCount": 2, "tags": {
                "turn_score": 3, "quality_labels": [], "issues": ["abrupt"],
                "rewrite_needed": True, "rewrite": "Hello, how can I help?"
            }},
            {"role": "user", "text": "What's the weather?"},
            {"role": "assistant", "text": "It's sunny today!", "turnCount": 4, "tags": {
                "turn_score": 8, "quality_labels": ["helpful"], "issues": [], "rewrite_needed": False
            }},
        ])

        records = convert_transcript_to_sharegpt(transcript, logger)

        # Only one record (turn 2 skipped, turn 4 creates record)
        assert len(records) == 1

        record = records[0]
        # History should contain: human("Hi"), gpt("Hello, how can I help?"), human("What's the weather?"), gpt("It's sunny!")
        assert len(record.conversations) == 4
        assert record.conversations[0].value == "Hi"
        assert record.conversations[1].value == "Hello, how can I help?"  # The rewrite, not "what"
        assert record.conversations[2].value == "What's the weather?"
        assert record.conversations[3].value == "It's sunny today!"
        assert record.meta.assistant_turn_index == 2

    def test_original_in_history_when_rewrite_missing(self, logger):
        """Test that original text is used in history when rewrite_needed but no rewrite provided."""
        transcript = create_tagged_transcript([
            {"role": "user", "text": "Hi"},
            {"role": "assistant", "text": "what", "turnCount": 2, "tags": {
                "turn_score": 3, "quality_labels": [], "issues": ["abrupt"],
                "rewrite_needed": True, "rewrite": None  # No rewrite available
            }},
            {"role": "user", "text": "What's the weather?"},
            {"role": "assistant", "text": "It's sunny today!", "turnCount": 4, "tags": {
                "turn_score": 8, "quality_labels": ["helpful"], "issues": [], "rewrite_needed": False
            }},
        ])

        records = convert_transcript_to_sharegpt(transcript, logger)

        # Only one record (turn 2 skipped)
        assert len(records) == 1

        record = records[0]
        # Falls back to original "what" since no rewrite exists
        assert record.conversations[1].value == "what"

    def test_skips_assistant_first_turn(self, logger):
        """Test that first assistant turn is skipped if no human message yet."""
        transcript = create_tagged_transcript([
            {"role": "assistant", "text": "Welcome to our service!", "turnCount": 1, "tags": {
                "turn_score": 8, "quality_labels": [], "issues": [], "rewrite_needed": False
            }},
            {"role": "user", "text": "I have a question"},
            {"role": "assistant", "text": "Go ahead!", "turnCount": 3, "tags": {
                "turn_score": 7, "quality_labels": [], "issues": [], "rewrite_needed": False
            }},
        ])

        records = convert_transcript_to_sharegpt(transcript, logger)

        # Only one record (for the second assistant turn)
        assert len(records) == 1
        assert records[0].meta.assistant_turn_index == 2

        # But history should include the first assistant message
        assert len(records[0].conversations) == 3
        assert records[0].conversations[0].value == "Welcome to our service!"

    def test_cumulative_history(self, logger):
        """Test that history accumulates across turns."""
        transcript = create_tagged_transcript([
            {"role": "user", "text": "Hi"},
            {"role": "assistant", "text": "Hello!", "turnCount": 2, "tags": {
                "turn_score": 8, "quality_labels": [], "issues": [], "rewrite_needed": False
            }},
            {"role": "user", "text": "What's the weather?"},
            {"role": "assistant", "text": "It's sunny!", "turnCount": 4, "tags": {
                "turn_score": 8, "quality_labels": [], "issues": [], "rewrite_needed": False
            }},
            {"role": "user", "text": "Thanks!"},
            {"role": "assistant", "text": "You're welcome!", "turnCount": 6, "tags": {
                "turn_score": 9, "quality_labels": [], "issues": [], "rewrite_needed": False
            }},
        ])

        records = convert_transcript_to_sharegpt(transcript, logger)

        assert len(records) == 3

        # First record: 2 messages (human + assistant)
        assert len(records[0].conversations) == 2

        # Second record: 4 messages (human + assistant + human + assistant)
        assert len(records[1].conversations) == 4

        # Third record: 6 messages (full history)
        assert len(records[2].conversations) == 6

    def test_metadata_tracking(self, logger):
        """Test that metadata correctly tracks conversation and turn info."""
        transcript = create_tagged_transcript([
            {"role": "user", "text": "Hi"},
            {"role": "assistant", "text": "Hello!", "turnCount": 2, "tags": {
                "turn_score": 8, "quality_labels": [], "issues": [], "rewrite_needed": False
            }},
        ])
        transcript.conversation_id = "conv_xyz789"

        records = convert_transcript_to_sharegpt(transcript, logger)

        assert records[0].meta.conversation_id == "conv_xyz789"
        assert records[0].meta.assistant_turn_index == 1

    def test_empty_transcript(self, logger):
        """Test handling of transcript with no turns."""
        transcript = create_tagged_transcript([])

        records = convert_transcript_to_sharegpt(transcript, logger)

        assert len(records) == 0

    def test_user_only_transcript(self, logger):
        """Test handling of transcript with only user messages."""
        transcript = create_tagged_transcript([
            {"role": "user", "text": "Hello?"},
            {"role": "user", "text": "Anyone there?"},
        ])

        records = convert_transcript_to_sharegpt(transcript, logger)

        assert len(records) == 0


class TestShareGPTModels:
    """Tests for ShareGPT data models."""

    def test_sharegpt_message_serialization(self):
        """Test ShareGPTMessage serializes with 'from' alias."""
        msg = ShareGPTMessage(from_="human", value="Hello")

        # Serialize with alias
        data = json.loads(msg.model_dump_json(by_alias=True))

        assert data["from"] == "human"
        assert data["value"] == "Hello"
        assert "from_" not in data

    def test_sharegpt_record_serialization(self):
        """Test ShareGPTRecord serializes with '_meta' alias."""
        record = ShareGPTRecord(
            conversations=[
                ShareGPTMessage(from_="human", value="Hi"),
                ShareGPTMessage(from_="gpt", value="Hello!"),
            ],
            meta=Metadata(
                conversation_id="test123",
                assistant_turn_index=1,
                used_rewrite=False,
            ),
        )

        data = json.loads(record.model_dump_json(by_alias=True))

        assert "_meta" in data
        assert "meta" not in data
        assert data["_meta"]["conversation_id"] == "test123"
        assert data["conversations"][0]["from"] == "human"

    def test_metadata_fields(self):
        """Test Metadata model fields."""
        meta = Metadata(
            conversation_id="conv123",
            assistant_turn_index=5,
            used_rewrite=True,
        )

        assert meta.conversation_id == "conv123"
        assert meta.assistant_turn_index == 5
        assert meta.used_rewrite is True


class TestShareGPTRecordFormat:
    """Tests for the expected output format matching Llama-Factory requirements."""

    def test_record_matches_expected_format(self, logger):
        """Test that output matches the expected ShareGPT format."""
        transcript = create_tagged_transcript([
            {"role": "user", "text": "What are your hours?"},
            {"role": "assistant", "text": "We're open 9-5!", "turnCount": 2, "tags": {
                "turn_score": 8, "quality_labels": [], "issues": [], "rewrite_needed": False
            }},
        ])

        records = convert_transcript_to_sharegpt(transcript, logger)
        data = json.loads(records[0].model_dump_json(by_alias=True))

        # Check structure matches expected format
        assert "conversations" in data
        assert "_meta" in data
        assert isinstance(data["conversations"], list)
        assert len(data["conversations"]) == 2

        # Check conversation format
        assert data["conversations"][0] == {"from": "human", "value": "What are your hours?"}
        assert data["conversations"][1] == {"from": "gpt", "value": "We're open 9-5!"}

        # Check metadata format
        assert data["_meta"]["conversation_id"] == "test123"
        assert data["_meta"]["assistant_turn_index"] == 1
        assert data["_meta"]["used_rewrite"] is False

    def test_history_includes_rewritten_text_for_skipped_turns(self, logger):
        """Test that history uses rewritten text from skipped turns."""
        transcript = create_tagged_transcript([
            {"role": "user", "text": "Hi"},
            {"role": "assistant", "text": "what", "turnCount": 2, "tags": {
                "turn_score": 3, "quality_labels": [], "issues": [],
                "rewrite_needed": True, "rewrite": "Hello, how can I help?"
            }},
            {"role": "user", "text": "What's the time?"},
            {"role": "assistant", "text": "It's noon.", "turnCount": 4, "tags": {
                "turn_score": 8, "quality_labels": [], "issues": [], "rewrite_needed": False
            }},
        ])

        records = convert_transcript_to_sharegpt(transcript, logger)

        # Only 1 record - first assistant turn is skipped (rewrite_needed=true)
        assert len(records) == 1

        # Record's history should contain the rewritten version from the skipped turn
        record = records[0]
        # Conversation: human("Hi"), gpt("Hello, how can I help?"), human("What's the time?"), gpt("It's noon.")
        assert len(record.conversations) == 4
        assert record.conversations[1].value == "Hello, how can I help?"

    def test_multiple_skipped_turns_in_sequence(self, logger):
        """Test multiple consecutive rewrite_needed turns are all skipped."""
        transcript = create_tagged_transcript([
            {"role": "user", "text": "Hi"},
            {"role": "assistant", "text": "what", "turnCount": 2, "tags": {
                "turn_score": 3, "quality_labels": [], "issues": [],
                "rewrite_needed": True, "rewrite": "Hello!"
            }},
            {"role": "user", "text": "Help me"},
            {"role": "assistant", "text": "why", "turnCount": 4, "tags": {
                "turn_score": 2, "quality_labels": [], "issues": [],
                "rewrite_needed": True, "rewrite": "I'd be happy to help!"
            }},
            {"role": "user", "text": "What time is it?"},
            {"role": "assistant", "text": "It's 3pm.", "turnCount": 6, "tags": {
                "turn_score": 8, "quality_labels": [], "issues": [], "rewrite_needed": False
            }},
        ])

        records = convert_transcript_to_sharegpt(transcript, logger)

        # Only 1 record - turns 2 and 4 are both skipped
        assert len(records) == 1

        record = records[0]
        # History should have all rewrites from skipped turns
        assert len(record.conversations) == 6
        assert record.conversations[1].value == "Hello!"  # Rewrite from turn 2
        assert record.conversations[3].value == "I'd be happy to help!"  # Rewrite from turn 4
        assert record.conversations[5].value == "It's 3pm."  # The training target
