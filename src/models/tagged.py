"""
Step 2 Output: Tagged Transcript Data Model

TaggedTranscript {
  conversation_id: string
  conversation_tags: ConversationTags
  turns: TaggedTurn[]
}

ConversationTags {
  call_type: string
  overall_quality: "good" | "mixed" | "poor"
  summary: string[]
}

TaggedTurn {
  role: "assistant" | "user"
  text: string
  turnCount: int (optional for user turns)
  timestamp: int (optional for user turns)
  tags: TurnTags (only present for assistant turns)
}

TurnTags {
  turn_score: int (1-10)
  quality_labels: string[]
  issues: string[]
  rewrite_needed: bool
  rewrite: string (optional, present if rewrite_needed=true)
}

Example:
{
  "conversation_id": "6aa47f9fbdab459b",
  "conversation_tags": {
    "call_type": "branch_inquiry",
    "overall_quality": "good",
    "summary": [
      "Caller asks about branch hours.",
      "Agent provides hours and offers further assistance."
    ]
  },
  "turns": [
    {
      "role": "assistant",
      "text": "hello this is harper valley national bank...",
      "turnCount": 1,
      "timestamp": 1591060816005,
      "tags": {
        "turn_score": 9,
        "quality_labels": ["polite", "professional"],
        "issues": [],
        "rewrite_needed": false
      }
    },
    {
      "role": "user",
      "text": "hi my name is michael johnson..."
    }
  ]
}
"""

from pydantic import BaseModel
from typing import Literal, Optional


class TurnTags(BaseModel):
    """Tags for an assistant turn."""
    turn_score: int
    quality_labels: list[str]
    issues: list[str]
    rewrite_needed: bool
    rewrite: Optional[str] = None


class ConversationTags(BaseModel):
    """Conversation-level tags and summary."""
    call_type: str
    overall_quality: Literal["good", "mixed", "poor"]
    summary: list[str]


class TaggedTurn(BaseModel):
    """A single turn in the tagged transcript."""
    role: Literal["assistant", "user"]
    text: str
    turnCount: Optional[int] = None
    timestamp: Optional[int] = None
    tags: Optional[TurnTags] = None


class TaggedTranscript(BaseModel):
    """Complete tagged transcript (Step 2 output)."""
    conversation_id: str
    conversation_tags: ConversationTags
    turns: list[TaggedTurn]
