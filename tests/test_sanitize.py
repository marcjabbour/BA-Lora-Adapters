"""Unit tests for Step 1: Sanitization."""

import pytest
from scripts.sanitize_transcripts import is_noise, sanitize_transcript, NOISE_PATTERNS


class TestIsNoise:
    """Tests for the is_noise function."""

    def test_noise_pattern_brackets(self):
        assert is_noise("[noise]") is True

    def test_noise_pattern_unk(self):
        assert is_noise("<unk>") is True

    def test_empty_string(self):
        assert is_noise("") is True

    def test_whitespace_only(self):
        assert is_noise("   ") is True
        assert is_noise("\t\n") is True

    def test_valid_text(self):
        assert is_noise("hello how can i help you") is False

    def test_noise_with_whitespace(self):
        assert is_noise("  [noise]  ") is True
        assert is_noise("  <unk>  ") is True


class TestRoleMapping:
    """Tests for role mapping from raw to sanitized format."""

    def test_agent_becomes_assistant(self):
        raw_turns = [
            {"human_transcript": "hello", "speaker_role": "agent", "start_timestamp_ms": 1000, "index": 1}
        ]
        result = sanitize_transcript(raw_turns, "test-id")
        assert result.turns[0].role == "assistant"

    def test_caller_becomes_user(self):
        raw_turns = [
            {"human_transcript": "hi there", "speaker_role": "caller", "start_timestamp_ms": 1000, "index": 1}
        ]
        result = sanitize_transcript(raw_turns, "test-id")
        assert result.turns[0].role == "user"

    def test_unknown_role_filtered(self):
        raw_turns = [
            {"human_transcript": "hello", "speaker_role": "unknown", "start_timestamp_ms": 1000, "index": 1}
        ]
        result = sanitize_transcript(raw_turns, "test-id")
        assert len(result.turns) == 0


class TestNoiseFiltering:
    """Tests for filtering out noise entries."""

    def test_noise_filtered(self):
        raw_turns = [
            {"human_transcript": "[noise]", "speaker_role": "agent", "start_timestamp_ms": 1000, "index": 1},
            {"human_transcript": "hello", "speaker_role": "agent", "start_timestamp_ms": 2000, "index": 2},
            {"human_transcript": "<unk>", "speaker_role": "agent", "start_timestamp_ms": 3000, "index": 3},
        ]
        result = sanitize_transcript(raw_turns, "test-id")
        assert len(result.turns) == 1
        assert result.turns[0].text == "hello"

    def test_empty_transcript_filtered(self):
        raw_turns = [
            {"human_transcript": "", "speaker_role": "agent", "start_timestamp_ms": 1000, "index": 1},
            {"human_transcript": "hello", "speaker_role": "agent", "start_timestamp_ms": 2000, "index": 2},
        ]
        result = sanitize_transcript(raw_turns, "test-id")
        assert len(result.turns) == 1


class TestTurnMerging:
    """Tests for merging consecutive same-speaker turns."""

    def test_consecutive_same_speaker_merged(self):
        raw_turns = [
            {"human_transcript": "hello", "speaker_role": "agent", "start_timestamp_ms": 1000, "index": 1},
            {"human_transcript": "how can i help", "speaker_role": "agent", "start_timestamp_ms": 2000, "index": 2},
        ]
        result = sanitize_transcript(raw_turns, "test-id")
        assert len(result.turns) == 1
        assert result.turns[0].text == "hello how can i help"
        assert result.turns[0].timestamp == 1000  # Keeps first timestamp

    def test_alternating_speakers_not_merged(self):
        raw_turns = [
            {"human_transcript": "hello", "speaker_role": "agent", "start_timestamp_ms": 1000, "index": 1},
            {"human_transcript": "hi", "speaker_role": "caller", "start_timestamp_ms": 2000, "index": 2},
            {"human_transcript": "how can i help", "speaker_role": "agent", "start_timestamp_ms": 3000, "index": 3},
        ]
        result = sanitize_transcript(raw_turns, "test-id")
        assert len(result.turns) == 3

    def test_merging_with_noise_in_between(self):
        """Noise should be filtered before merging, so same-speaker turns with noise between them merge."""
        raw_turns = [
            {"human_transcript": "hello", "speaker_role": "agent", "start_timestamp_ms": 1000, "index": 1},
            {"human_transcript": "[noise]", "speaker_role": "agent", "start_timestamp_ms": 1500, "index": 2},
            {"human_transcript": "how can i help", "speaker_role": "agent", "start_timestamp_ms": 2000, "index": 3},
        ]
        result = sanitize_transcript(raw_turns, "test-id")
        assert len(result.turns) == 1
        assert result.turns[0].text == "hello how can i help"


class TestTurnCount:
    """Tests for sequential turn count assignment."""

    def test_turn_count_sequential(self):
        raw_turns = [
            {"human_transcript": "hello", "speaker_role": "agent", "start_timestamp_ms": 1000, "index": 1},
            {"human_transcript": "hi", "speaker_role": "caller", "start_timestamp_ms": 2000, "index": 2},
            {"human_transcript": "how can i help", "speaker_role": "agent", "start_timestamp_ms": 3000, "index": 3},
        ]
        result = sanitize_transcript(raw_turns, "test-id")
        assert result.turns[0].turnCount == 1
        assert result.turns[1].turnCount == 2
        assert result.turns[2].turnCount == 3

    def test_turn_count_after_merge(self):
        raw_turns = [
            {"human_transcript": "hello", "speaker_role": "agent", "start_timestamp_ms": 1000, "index": 1},
            {"human_transcript": "welcome", "speaker_role": "agent", "start_timestamp_ms": 1500, "index": 2},
            {"human_transcript": "hi", "speaker_role": "caller", "start_timestamp_ms": 2000, "index": 3},
        ]
        result = sanitize_transcript(raw_turns, "test-id")
        assert len(result.turns) == 2
        assert result.turns[0].turnCount == 1  # Merged agent turn
        assert result.turns[1].turnCount == 2  # Caller turn


class TestSortingByIndex:
    """Tests for proper sorting of turns by index."""

    def test_out_of_order_turns_sorted(self):
        raw_turns = [
            {"human_transcript": "third", "speaker_role": "agent", "start_timestamp_ms": 3000, "index": 3},
            {"human_transcript": "first", "speaker_role": "agent", "start_timestamp_ms": 1000, "index": 1},
            {"human_transcript": "second", "speaker_role": "caller", "start_timestamp_ms": 2000, "index": 2},
        ]
        result = sanitize_transcript(raw_turns, "test-id")
        assert result.turns[0].text == "first"
        assert result.turns[1].text == "second"
        assert result.turns[2].text == "third"


class TestConversationId:
    """Tests for conversation ID preservation."""

    def test_conversation_id_preserved(self):
        raw_turns = [
            {"human_transcript": "hello", "speaker_role": "agent", "start_timestamp_ms": 1000, "index": 1}
        ]
        result = sanitize_transcript(raw_turns, "my-conversation-123")
        assert result.conversation_id == "my-conversation-123"


class TestEmptyInput:
    """Tests for edge cases with empty input."""

    def test_empty_turns_list(self):
        result = sanitize_transcript([], "test-id")
        assert result.conversation_id == "test-id"
        assert len(result.turns) == 0

    def test_all_noise_filtered(self):
        raw_turns = [
            {"human_transcript": "[noise]", "speaker_role": "agent", "start_timestamp_ms": 1000, "index": 1},
            {"human_transcript": "<unk>", "speaker_role": "caller", "start_timestamp_ms": 2000, "index": 2},
        ]
        result = sanitize_transcript(raw_turns, "test-id")
        assert len(result.turns) == 0
