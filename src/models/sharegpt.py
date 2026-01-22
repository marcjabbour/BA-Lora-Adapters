"""
Step 3 Output: ShareGPT Data Model

ShareGPTDataset = ShareGPTRecord[]

ShareGPTRecord {
  conversations: Message[]
}

Message {
  from: "gpt" | "human"
  value: string
}

Note: ShareGPT format requires the first message to be from "human".
If the transcript starts with an assistant turn, we prepend an empty human message.

Example (one record per assistant turn, cumulative history):
[
  {
    "conversations": [
      {"from": "human", "value": ""},
      {"from": "gpt", "value": "hello this is harper valley national bank..."},
      {"from": "human", "value": "hi my name is michael johnson..."},
      {"from": "gpt", "value": "Great question, Michael! Our branch hours are..."}
    ]
  }
]
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional


class ShareGPTMessage(BaseModel):
    """A single message in ShareGPT format."""
    model_config = ConfigDict(populate_by_name=True)

    from_: Literal["gpt", "human"] = Field(alias="from")
    value: str


class ShareGPTRecord(BaseModel):
    """A single ShareGPT training record."""
    model_config = ConfigDict(populate_by_name=True)

    conversations: list[ShareGPTMessage]
