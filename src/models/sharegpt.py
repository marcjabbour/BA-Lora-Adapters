"""
Step 3 Output: ShareGPT Data Model

ShareGPTDataset = ShareGPTRecord[]

ShareGPTRecord {
  conversations: Message[]
  _meta: Metadata
}

Message {
  from: "gpt" | "human"
  value: string
}

Metadata {
  conversation_id: string
  assistant_turn_index: int
  used_rewrite: bool
}

Example (one record per assistant turn, cumulative history):
[
  {
    "conversations": [
      {"from": "gpt", "value": "hello this is harper valley national bank..."},
      {"from": "human", "value": "hi my name is michael johnson..."},
      {"from": "gpt", "value": "Great question, Michael! Our branch hours are..."}
    ],
    "_meta": {
      "conversation_id": "6aa47f9fbdab459b",
      "assistant_turn_index": 2,
      "used_rewrite": true
    }
  }
]
"""

from pydantic import BaseModel, Field
from typing import Literal


class ShareGPTMessage(BaseModel):
    """A single message in ShareGPT format."""
    from_: Literal["gpt", "human"] = Field(alias="from")
    value: str

    class Config:
        populate_by_name = True


class Metadata(BaseModel):
    """Metadata for traceability."""
    conversation_id: str
    assistant_turn_index: int
    used_rewrite: bool


class ShareGPTRecord(BaseModel):
    """A single ShareGPT training record."""
    conversations: list[ShareGPTMessage]
    _meta: Metadata = Field(alias="_meta")

    class Config:
        populate_by_name = True
