"""
Step 1 Output: Sanitized Transcript Data Model

SanitizedTranscript {
  conversation_id: string
  turns: SanitizedTurn[]
}

SanitizedTurn {
  role: "assistant" | "user"
  text: string
  turnCount: int (1-indexed)
  timestamp: int (unix ms)
}

Example:
{
  "conversation_id": "6aa47f9fbdab459b",
  "turns": [
    {
      "role": "assistant",
      "text": "hello this is harper valley national bank my name is robert how can i help you today",
      "turnCount": 1,
      "timestamp": 1591060816005
    },
    {
      "role": "user",
      "text": "hi my name is michael johnson what are the local branch hours",
      "turnCount": 2,
      "timestamp": 1591060822505
    }
  ]
}
"""

from pydantic import BaseModel
from typing import Literal


class SanitizedTurn(BaseModel):
    """A single turn in the sanitized transcript."""
    role: Literal["assistant", "user"]
    text: str
    turnCount: int
    timestamp: int


class SanitizedTranscript(BaseModel):
    """Complete sanitized transcript (Step 1 output)."""
    conversation_id: str
    turns: list[SanitizedTurn]
