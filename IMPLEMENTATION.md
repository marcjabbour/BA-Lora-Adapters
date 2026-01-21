# LoRA Adapter Data Pipeline - Implementation Plan

## Overview

Build a 5-step data pipeline for preparing customer-agent transcripts for LoRA adapter training via Llama-Factory SFT. This plan focuses on **Steps 1-3** (Sanitization, Tagging, Exporting).

**Configuration Decisions:**
- LLM Provider: **OpenAI GPT-4**
- Rewrite Threshold: **Below 5/10**

**Implementation Approach:**
- First create the skeleton (folder structure, empty files with stubs)
- Then implement each step one at a time as instructed

---

## Raw Input Format (Confirmed)

Each input file is a JSON array of turn objects with these relevant fields:
- `human_transcript`: The text content of the turn
- `speaker_role`: Either `"agent"` or `"caller"`
- `start_timestamp_ms`: Unix timestamp in milliseconds
- `index`: Turn sequence number

Example shows consecutive same-speaker turns (caller index 2 & 3) that Step 1 will merge.

---

## Project Structure

```
BA-LoRA-Adapters/
├── requirements.txt
├── .env.example
│
├── configs/
│   └── llm_config.yaml              # LLM provider settings
│
├── prompts/
│   └── tagging/
│       └── tagging_prompt.txt       # Tagging/rewriting prompt
│
├── data/
│   ├── raw/                         # Input: Original JSON transcripts
│   ├── Step-1-Sanitization/
│   │   └── output/                  # Sanitized transcripts
│   ├── Step-2-Tagging/
│   │   ├── output/                  # Tagged transcripts with rewrites
│   │   └── checkpoints/             # Resumable checkpoints
│   ├── Step-3-Exporting/
│   │   └── output/                  # ShareGPT format files
│   ├── Step-4-Training/             # (future)
│   └── Step-5-Serving/              # (future)
│
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── sanitized.py             # Step 1 output model
│   │   ├── tagged.py                # Step 2 output model
│   │   └── sharegpt.py              # Step 3 output model
│   ├── llm/
│   │   ├── __init__.py
│   │   └── client.py                # LLM client abstraction
│   └── utils/
│       ├── __init__.py
│       └── logging_utils.py
│
└── scripts/
    ├── sanitize_transcripts.py      # Step 1 CLI
    ├── tag_transcripts.py           # Step 2 CLI
    └── export_to_sharegpt.py        # Step 3 CLI
```

---

## Data Models (Type Schemas)

### Step 1 Output: Sanitized Transcript Data Model

```
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
```

<details>
<summary>Example</summary>

```json
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
    },
    {
      "role": "assistant",
      "text": "the branch hours are nine thirty a m to five o'clock p m",
      "turnCount": 3,
      "timestamp": 1591060831035
    }
  ]
}
```

</details>

### Step 2 Output: Tagged Transcript Data Model

```
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
```

<details>
<summary>Example</summary>

```json
{
  "conversation_id": "6aa47f9fbdab459b",
  "conversation_tags": {
    "call_type": "branch_inquiry",
    "overall_quality": "good",
    "summary": [
      "Caller asks about branch hours.",
      "Agent provides hours and offers further assistance.",
      "Caller thanks agent and ends call."
    ]
  },
  "turns": [
    {
      "role": "assistant",
      "text": "hello this is harper valley national bank my name is robert how can i help you today",
      "turnCount": 1,
      "timestamp": 1591060816005,
      "tags": {
        "turn_score": 9,
        "quality_labels": ["polite", "professional", "clear"],
        "issues": [],
        "rewrite_needed": false
      }
    },
    {
      "role": "user",
      "text": "hi my name is michael johnson what are the local branch hours"
    },
    {
      "role": "assistant",
      "text": "the branch hours are nine thirty a m to five o'clock p m",
      "turnCount": 3,
      "timestamp": 1591060831035,
      "tags": {
        "turn_score": 6,
        "quality_labels": ["informative"],
        "issues": ["abrupt", "no_acknowledgment"],
        "rewrite_needed": true,
        "rewrite": "Great question, Michael! Our branch hours are 9:30 AM to 5:00 PM, Monday through Friday."
      }
    },
    {
      "role": "assistant",
      "text": "is there anything else i can help you with",
      "turnCount": 4,
      "timestamp": 1591060836335,
      "tags": {
        "turn_score": 8,
        "quality_labels": ["polite", "helpful"],
        "issues": [],
        "rewrite_needed": false
      }
    }
  ]
}
```

</details>

### Step 3 Output: ShareGPT Data Model

```
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
```

<details>
<summary>Example (one record per assistant turn, cumulative history)</summary>

```json
[
  {
    "conversations": [
      {"from": "gpt", "value": "hello this is harper valley national bank my name is robert how can i help you today"},
      {"from": "human", "value": "hi my name is michael johnson what are the local branch hours"},
      {"from": "gpt", "value": "Great question, Michael! Our branch hours are 9:30 AM to 5:00 PM, Monday through Friday."}
    ],
    "_meta": {
      "conversation_id": "6aa47f9fbdab459b",
      "assistant_turn_index": 2,
      "used_rewrite": true
    }
  },
  {
    "conversations": [
      {"from": "gpt", "value": "hello this is harper valley national bank my name is robert how can i help you today"},
      {"from": "human", "value": "hi my name is michael johnson what are the local branch hours"},
      {"from": "gpt", "value": "Great question, Michael! Our branch hours are 9:30 AM to 5:00 PM, Monday through Friday."},
      {"from": "human", "value": "no thank you that's all the help i needed today"},
      {"from": "gpt", "value": "thank you for calling have a great day"}
    ],
    "_meta": {
      "conversation_id": "6aa47f9fbdab459b",
      "assistant_turn_index": 3,
      "used_rewrite": false
    }
  }
]
```

</details>

---

## Implementation Steps

### Step 1: Sanitization (`scripts/sanitize_transcripts.py`)

**Status:** ✅ Implemented

**Input**: Directory of raw JSON transcripts with fields: `human_transcript`, `speaker_role`, `start_timestamp_ms`

**Operations**:
1. Filter noise entries (configurable patterns like `[noise]`, `<unk>`)
2. Map roles: `agent` → `assistant`, `caller` → `user`
3. Join consecutive same-speaker turns
4. Assign sequential `turnCount`

**CLI**:
```bash
python scripts/sanitize_transcripts.py \
  --input data/raw/ \
  --output data/Step-1-Sanitization/output/
```

---

### Step 2: Tagging (`scripts/tag_transcripts.py`)

**Status:** ✅ Implemented

**Input**: Sanitized transcripts from Step 1

**Operations**:
1. For each conversation, send to LLM for evaluation
2. LLM returns per-turn scores, quality labels, issues
3. Determine if rewrite needed (score < threshold)
4. Generate rewrites for poor responses
5. Create conversation-level summary

**CLI**:
```bash
python scripts/tag_transcripts.py \
  --input data/Step-1-Sanitization/output/ \
  --output data/Step-2-Tagging/output/ \
  --provider openai
```

**Default LLM**: OpenAI GPT-4 (configurable to Anthropic or local vLLM/Ollama)

---

### Step 3: Exporting (`scripts/export_to_sharegpt.py`)

**Status:** ⬜ Not implemented

**Input**: Tagged transcripts from Step 2

**Algorithm** (per user specification):
1. Initialize empty `records` and `history` lists
2. For each turn:
   - If `user`: add to history as `{"from": "human", "value": text}`
   - If `assistant`:
     - If `rewrite_needed=true` and rewrite exists, use rewrite
     - Skip if no human message yet in history
     - Create ShareGPT record: `history + [assistant message]`
     - Add to history for future records
3. Output as JSON/JSONL

**CLI**:
```bash
python scripts/export_to_sharegpt.py \
  --input data/Step-2-Tagging/output/ \
  --output data/Step-3-Exporting/output/
```

---

## Files to Create

| File | Purpose | Status |
|------|---------|--------|
| `requirements.txt` | Dependencies (pydantic, anthropic, openai, etc.) | ✅ |
| `.env.example` | Template for API keys | ✅ |
| `configs/llm_config.yaml` | LLM provider configuration | ✅ |
| `prompts/tagging/tagging_prompt.txt` | Tagging prompt template | ✅ |
| `src/models/sanitized.py` | Pydantic model for Step 1 | ✅ |
| `src/models/tagged.py` | Pydantic model for Step 2 | ✅ |
| `src/models/sharegpt.py` | Pydantic model for Step 3 | ✅ |
| `src/llm/client.py` | LLM client abstraction | ✅ |
| `src/utils/logging_utils.py` | Logging configuration | ✅ |
| `scripts/sanitize_transcripts.py` | Step 1 CLI | ✅ |
| `scripts/tag_transcripts.py` | Step 2 CLI | ✅ |
| `scripts/export_to_sharegpt.py` | Step 3 CLI | ⬜ |

---

## Verification

1. **Step 1**: Run with sample raw transcript, verify output matches Sanitized Transcript Data Model
2. **Step 2**: Run with sanitized transcript, verify LLM calls work and output matches Tagged Data Model
3. **Step 3**: Run with tagged transcript, verify ShareGPT format is correct for Llama-Factory
4. **End-to-end**: Process a sample file through all 3 steps, validate final output

---

## Configuration

### Noise Patterns (Step 1)
Filter turns where `human_transcript` matches:
- `[noise]`
- `<unk>`
- Empty/whitespace-only strings

### Rewrite Threshold (Step 2)
- Score below **5** (on 1-10 scale) triggers a rewrite
- LLM evaluates: clarity, helpfulness, professionalism, empathy

### LLM Config (Step 2)
```yaml
provider: openai
model: gpt-4o
temperature: 0.1
max_tokens: 4096
```
