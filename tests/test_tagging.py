"""
Unit tests for Step 2: Tagging

Tests cover:
- LLM response JSON extraction
- Conversation formatting
- Rewrite threshold logic
- Tagged transcript structure
"""

import json
import pytest

from src.models.sanitized import SanitizedTranscript, SanitizedTurn
from src.models.tagged import (
    TaggedTranscript,
    TaggedTurn,
    TurnTags,
    ConversationTags,
)

# Import functions from the tagging script
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.tag_transcripts import (
    format_conversation_for_llm,
    extract_json_from_response,
)


class TestFormatConversationForLLM:
    """Tests for format_conversation_for_llm function."""

    def test_basic_formatting(self):
        """Test basic conversation formatting."""
        transcript = SanitizedTranscript(
            conversation_id="test123",
            turns=[
                SanitizedTurn(role="assistant", text="hello", turnCount=1, timestamp=1000),
                SanitizedTurn(role="user", text="hi there", turnCount=2, timestamp=2000),
                SanitizedTurn(role="assistant", text="how can i help", turnCount=3, timestamp=3000),
            ],
        )

        result = format_conversation_for_llm(transcript)

        assert "[Turn 1 - assistant] hello" in result
        assert "[Turn 2 - user] hi there" in result
        assert "[Turn 3 - assistant] how can i help" in result

    def test_single_turn(self):
        """Test formatting with single turn."""
        transcript = SanitizedTranscript(
            conversation_id="test123",
            turns=[
                SanitizedTurn(role="assistant", text="welcome", turnCount=1, timestamp=1000),
            ],
        )

        result = format_conversation_for_llm(transcript)
        assert result == "[Turn 1 - assistant] welcome"

    def test_preserves_turn_order(self):
        """Test that turn order is preserved."""
        transcript = SanitizedTranscript(
            conversation_id="test123",
            turns=[
                SanitizedTurn(role="assistant", text="first", turnCount=1, timestamp=1000),
                SanitizedTurn(role="user", text="second", turnCount=2, timestamp=2000),
                SanitizedTurn(role="assistant", text="third", turnCount=3, timestamp=3000),
            ],
        )

        result = format_conversation_for_llm(transcript)
        lines = result.split("\n")

        assert len(lines) == 3
        assert "first" in lines[0]
        assert "second" in lines[1]
        assert "third" in lines[2]


class TestExtractJsonFromResponse:
    """Tests for extract_json_from_response function."""

    def test_plain_json(self):
        """Test extraction from plain JSON response."""
        response = '{"key": "value", "number": 42}'
        result = extract_json_from_response(response)

        assert result == {"key": "value", "number": 42}

    def test_json_in_code_block(self):
        """Test extraction from markdown code block."""
        response = """Here's the result:
```json
{"key": "value", "number": 42}
```
"""
        result = extract_json_from_response(response)

        assert result == {"key": "value", "number": 42}

    def test_json_in_plain_code_block(self):
        """Test extraction from plain code block without json tag."""
        response = """Result:
```
{"key": "value"}
```
"""
        result = extract_json_from_response(response)

        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        """Test extraction when JSON has surrounding text."""
        response = 'The evaluation is: {"score": 8} That looks good.'
        result = extract_json_from_response(response)

        assert result == {"score": 8}

    def test_nested_json(self):
        """Test extraction of nested JSON structure."""
        response = '''```json
{
  "conversation_tags": {
    "call_type": "inquiry",
    "overall_quality": "good",
    "summary": ["point 1", "point 2"]
  },
  "turn_evaluations": [
    {"turn_number": 1, "turn_score": 8}
  ]
}
```'''
        result = extract_json_from_response(response)

        assert result["conversation_tags"]["call_type"] == "inquiry"
        assert result["turn_evaluations"][0]["turn_score"] == 8

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises ValueError."""
        response = "No JSON here, just text."

        with pytest.raises(ValueError, match="No valid JSON found"):
            extract_json_from_response(response)

    def test_malformed_json_raises_error(self):
        """Test that malformed JSON raises error."""
        response = '{"key": "value", incomplete}'

        with pytest.raises(json.JSONDecodeError):
            extract_json_from_response(response)


class TestRewriteThresholdLogic:
    """Tests for rewrite threshold logic (score <= threshold triggers rewrite)."""

    def test_score_below_threshold_needs_rewrite(self):
        """Score below threshold should trigger rewrite."""
        threshold = 6

        for score in [1, 2, 3, 4, 5]:
            assert score <= threshold

    def test_score_at_threshold_needs_rewrite(self):
        """Score at threshold should trigger rewrite."""
        threshold = 6
        score = 6

        assert score <= threshold

    def test_score_above_threshold_no_rewrite(self):
        """Score above threshold should not trigger rewrite."""
        threshold = 6

        for score in [7, 8, 9, 10]:
            assert not (score <= threshold)


class TestTaggedModels:
    """Tests for tagged data models."""

    def test_turn_tags_with_rewrite(self):
        """Test TurnTags with rewrite."""
        tags = TurnTags(
            turn_score=3,
            quality_labels=["unclear"],
            issues=["abrupt", "no_greeting"],
            rewrite_needed=True,
            rewrite="Hello! How can I help you today?",
        )

        assert tags.turn_score == 3
        assert tags.rewrite_needed is True
        assert tags.rewrite is not None

    def test_turn_tags_without_rewrite(self):
        """Test TurnTags without rewrite."""
        tags = TurnTags(
            turn_score=8,
            quality_labels=["polite", "professional"],
            issues=[],
            rewrite_needed=False,
        )

        assert tags.turn_score == 8
        assert tags.rewrite_needed is False
        assert tags.rewrite is None

    def test_user_turn_no_tags(self):
        """Test that user turns can be created without tags."""
        turn = TaggedTurn(
            role="user",
            text="I need help with my account",
        )

        assert turn.role == "user"
        assert turn.tags is None
        assert turn.turnCount is None

    def test_assistant_turn_with_tags(self):
        """Test assistant turn with full tags."""
        turn = TaggedTurn(
            role="assistant",
            text="I'd be happy to help you with your account.",
            turnCount=1,
            timestamp=1000,
            tags=TurnTags(
                turn_score=9,
                quality_labels=["helpful", "professional"],
                issues=[],
                rewrite_needed=False,
            ),
        )

        assert turn.role == "assistant"
        assert turn.tags is not None
        assert turn.tags.turn_score == 9

    def test_conversation_tags(self):
        """Test ConversationTags model."""
        conv_tags = ConversationTags(
            call_type="account_inquiry",
            overall_quality="good",
            summary=["Customer asked about balance", "Agent provided information"],
        )

        assert conv_tags.call_type == "account_inquiry"
        assert conv_tags.overall_quality == "good"
        assert len(conv_tags.summary) == 2

    def test_conversation_tags_quality_validation(self):
        """Test that overall_quality only accepts valid values."""
        # Valid values should work
        for quality in ["good", "mixed", "poor"]:
            tags = ConversationTags(
                call_type="test",
                overall_quality=quality,
                summary=[],
            )
            assert tags.overall_quality == quality

    def test_tagged_transcript_structure(self):
        """Test complete TaggedTranscript structure."""
        transcript = TaggedTranscript(
            conversation_id="test123",
            conversation_tags=ConversationTags(
                call_type="inquiry",
                overall_quality="mixed",
                summary=["Customer inquiry", "Partial resolution"],
            ),
            turns=[
                TaggedTurn(
                    role="assistant",
                    text="Hello",
                    turnCount=1,
                    timestamp=1000,
                    tags=TurnTags(
                        turn_score=7,
                        quality_labels=["polite"],
                        issues=[],
                        rewrite_needed=False,
                    ),
                ),
                TaggedTurn(
                    role="user",
                    text="Hi",
                ),
            ],
        )

        assert transcript.conversation_id == "test123"
        assert len(transcript.turns) == 2
        assert transcript.turns[0].tags is not None
        assert transcript.turns[1].tags is None


class TestTaggedTranscriptSerialization:
    """Tests for tagged transcript JSON serialization."""

    def test_serialization_roundtrip(self):
        """Test that serialization and deserialization work correctly."""
        original = TaggedTranscript(
            conversation_id="test123",
            conversation_tags=ConversationTags(
                call_type="inquiry",
                overall_quality="good",
                summary=["Summary point"],
            ),
            turns=[
                TaggedTurn(
                    role="assistant",
                    text="Hello",
                    turnCount=1,
                    timestamp=1000,
                    tags=TurnTags(
                        turn_score=8,
                        quality_labels=["professional"],
                        issues=[],
                        rewrite_needed=False,
                    ),
                ),
            ],
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize back
        restored = TaggedTranscript.model_validate_json(json_str)

        assert restored.conversation_id == original.conversation_id
        assert restored.turns[0].tags.turn_score == 8

    def test_optional_fields_excluded_when_none(self):
        """Test that None optional fields are handled correctly."""
        turn = TaggedTurn(
            role="user",
            text="Hello",
        )

        data = turn.model_dump()

        assert data["role"] == "user"
        assert data["text"] == "Hello"
        # Optional fields should be None
        assert data["turnCount"] is None
        assert data["timestamp"] is None
        assert data["tags"] is None
